"""Import a WhatsApp group chat export into the knowledge base — carefully.

How to get the file: WhatsApp → open the group → ⋮ (Android) or group name (iPhone) → More → Export chat →
Without media. You get a .txt file (or a .zip with the .txt inside).

What we keep and what we drop:
  * Only messages about Beldex / crypto topics, at least a short sentence long.
  * Sender names and phone numbers are removed (shown as "Member"), so nobody's identity is stored.
  * Email addresses and phone numbers inside messages are masked.
  * System lines ("joined", "deleted", "<Media omitted>") are dropped.
  * Each day becomes one passage marked kind="community" — the assistant must say it is from the
    community chat and unverified, and must prefer official sources when they disagree.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime

from app.config import settings

KDIR = settings.data_dir / "knowledge"
PREFIX = "community_"

# 12/11/2026, 21:05 - Name: text      (Android)
# [12/11/26, 9:05:12 PM] Name: text   (iPhone)
LINE = re.compile(
    r"^‎?\[?(?P<d>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}),?\s+(?P<t>\d{1,2}[:.]\d{2}(?:[:.]\d{2})?(?:\s?[APap]\.?[Mm]\.?)?)\]?\s*[-–]?\s*"
    r"(?P<who>[^:]{1,60}):\s(?P<msg>.*)$")
SYSTEM = re.compile(r"(<Media omitted>|image omitted|video omitted|sticker omitted|audio omitted|document omitted|"
                    r"This message was deleted|You deleted this message|Messages and calls are end-to-end encrypted|"
                    r"<This message was edited>|joined using this group's invite link|null$)", re.I)
TOPIC = re.compile(r"(beldex|\bbdx\b|masternode|bchat|belnet|\bbns\b|beldex browser|wallet|stak|bridge|hardfork|"
                   r"listing|listed|exchange|kraken|mexc|kucoin|mica|europe|regulat|licen|burn|token|privacy|"
                   r"update|launch|roadmap|airdrop|nexus|withdraw|deposit|scam|fraud|price|bitcoin|crypto|"
                   r"பெல்டெக்ஸ்|மாஸ்டர்|வாலட்|ஸ்டேக்|கிரிப்டோ|அப்டேட்|எக்ஸ்சேஞ்ச்)", re.I)
PHONE = re.compile(r"(?:\+?\d[\d\s-]{8,}\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
TAMIL = re.compile(r"[஀-௿]")


def _read(raw: bytes) -> str:
    if raw[:2] == b"PK":  # .zip export
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            txt = [n for n in z.namelist() if n.lower().endswith(".txt")]
            if not txt:
                raise ValueError("The .zip has no chat .txt file inside. Export the chat again 'Without media'.")
            raw = z.read(txt[0])
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not read the file.")


def _date(s: str) -> str:
    parts = re.split(r"[/.-]", s)
    if len(parts[2]) == 2:
        parts[2] = "20" + parts[2]
    d, m, y = (int(p) for p in parts)
    if m > 12:  # US format month/day/year
        d, m = m, d
    try:
        return datetime(y, m, d).strftime("%Y-%m-%d")
    except ValueError:
        return f"{y:04d}-01-01"


def parse(raw: bytes) -> list[dict]:
    """Returns [{date, text}] — one cleaned message each, names removed."""
    text = _read(raw)
    msgs: list[dict] = []
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if m:
            msgs.append({"date": _date(m["d"]), "text": m["msg"].strip()})
        elif msgs and line.strip():  # continuation of a multi-line message
            msgs[-1]["text"] += " " + line.strip()
    out = []
    for m in msgs:
        t = m["text"]
        if SYSTEM.search(t) and len(t) < 80:
            continue
        t = EMAIL.sub("[email hidden]", PHONE.sub("[number hidden]", t))
        if len(t) < 25 or not TOPIC.search(t):
            continue
        out.append({"date": m["date"], "text": t[:1200]})
    return out


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "group"


def import_chat(raw: bytes, group: str) -> dict:
    msgs = parse(raw)
    if not msgs:
        raise ValueError("No Beldex-related messages were found. Check that this is a WhatsApp 'Export chat' .txt file.")
    by_day: dict[str, list[str]] = {}
    for m in msgs:
        by_day.setdefault(m["date"], []).append(m["text"])
    slug = _slug(group)
    rows = []
    for day, items in sorted(by_day.items()):
        body = "\n".join(f"- Member: {t}" for t in items)
        rows.append({
            "title": f"{group} — community chat {day} (unverified)",
            "url": f"https://whatsapp.local/{slug}#{day}",
            "published": day, "kind": "community",
            "lang": "ta" if len(TAMIL.findall(body)) > len(body) * 0.15 else "en",
            "text": (f"Messages shared by members of the '{group}' WhatsApp group on {day}. These are community "
                     f"messages, not official Beldex statements, and have not been verified.\n{body}"),
        })
    KDIR.mkdir(parents=True, exist_ok=True)
    (KDIR / f"{PREFIX}{slug}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
                                                encoding="utf-8")
    return {"group": group, "file": f"{PREFIX}{slug}.jsonl", "messages": len(msgs), "days": len(rows),
            "from": rows[0]["published"], "to": rows[-1]["published"]}


def list_imports() -> list[dict]:
    out = []
    for f in sorted(KDIR.glob(f"{PREFIX}*.jsonl")):
        rows = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if rows:
            out.append({"file": f.name, "group": rows[0]["title"].split(" — ")[0], "days": len(rows),
                        "messages": sum(r["text"].count("\n- Member:") for r in rows),
                        "from": rows[0]["published"], "to": rows[-1]["published"],
                        "imported_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes")})
    return out


def delete_import(name: str) -> bool:
    f = KDIR / name
    if not name.startswith(PREFIX) or "/" in name or not f.exists():
        return False
    f.unlink()
    return True
