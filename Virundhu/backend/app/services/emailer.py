"""Send email over SMTP. With no SMTP_HOST set, emails are written to the log instead."""

import html as htmlmod
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from app.config import settings

logger = logging.getLogger(__name__)


URL_LINE = re.compile(r"^\s*(https?://\S+)\s*$")
FOREST, CREAM, TURMERIC, INK, SOFT = "#0c3b2e", "#fff8ee", "#f8b62d", "#17251f", "#55625b"


def sender() -> str:
    """'Virundhu <address>' so inboxes show Virundhu as the sender (Gmail sends from the signed-in address)."""
    name, addr = parseaddr(settings.EMAIL_FROM)
    if not addr or "example.com" in addr or "yourdomain" in addr:
        addr = settings.SMTP_USER or addr
    return formataddr((name or "Virundhu", addr))


def _button_label(url: str) -> str:
    if "reset-password" in url:
        return "Choose a new password"
    if "forgot-password" in url:
        return "It wasn't me: reset my password"
    if "verify-email" in url:
        return "Confirm my email"
    if "/receipt/" in url:
        return "View or print receipt"
    if "/billing" in url or "pay" in url:
        return "Renew or choose a plan"
    if "/support" in url:
        return "Open your request"
    if "/join" in url or "invite" in url:
        return "Accept the invitation"
    if "/inbox" in url or "/alerts" in url:
        return "Open in Virundhu"
    return "Open Virundhu"


CHILLI = "#e8492a"

# kind: (headline, sub-line, accent colour, quote). Quotes are Virundhu's own lines.
KINDS = {
    "welcome": (
        "Your table is set.",
        "14 days free. Every review, every language, heard.",
        TURMERIC,
        "Every great restaurant started with one first service. Here's to yours.",
    ),
    "reset": (
        "Let's get you back in.",
        "One tap below. The link works once, for 30 minutes.",
        TURMERIC,
        "A good kitchen keeps its doors open for guests and locked to strangers.",
    ),
    "changed": (
        "Your password was changed.",
        "If this was you, you're all set. If not, act now.",
        TURMERIC,
        "The best hosts check every door before the evening rush.",
    ),
    "countdown": (
        "{n} left on your plan.",
        "Keep every guest heard without a break.",
        TURMERIC,
        "Guests forget a meal. They remember how they were treated.",
    ),
    "ended": (
        "Your plan has paused.",
        "Your reviews and settings are safe. Pick up right where you left off.",
        TURMERIC,
        "The door is always open. Your guests are still talking; let's listen again.",
    ),
    "suspended": (
        "Your account is suspended.",
        "Your free period is over. Your reviews and settings are safe; renew to switch everything back on.",
        CHILLI,
        "The door is always open. Your guests are still talking; let's listen again.",
    ),
    "receipt": (
        "Payment received. Thank you!",
        "Your receipt details are below.",
        "#2bb673",
        "Thank you for trusting us with your guests' voices.",
    ),
    "urgent": (
        "A guest needs you now.",
        "A serious review just came in. A quick, kind reply makes all the difference.",
        CHILLI,
        "One fast, honest reply can turn an upset guest into your loudest fan.",
    ),
    "support": (
        "We're on it.",
        "A real person reads every message.",
        TURMERIC,
        "Every question you ask makes Virundhu better for every restaurant.",
    ),
    "default": ("", "", TURMERIC, "Good food fills the plate. Being heard fills the heart."),
}


def email_kind(subject: str) -> str:
    s = subject.lower()
    if s.startswith("welcome"):
        return "welcome"
    if "reset your" in s:
        return "reset"
    if "password was changed" in s:
        return "changed"
    if " ends in " in s:
        return "countdown"
    if "suspended" in s:
        return "suspended"
    if "has ended" in s:
        return "ended"
    if s.startswith(("payment received", "receipt")):
        return "receipt"
    if s.startswith("urgent"):
        return "urgent"
    if "request" in s or s.startswith(("reply on", "we've got your")):
        return "support"
    return "default"


def closing_text(subject: str = "") -> str:
    return "\n\nThank you so much,\nTeam Virundhu\n\n\u201c" + KINDS[email_kind(subject)][3] + "\u201d\n"


def _cell(content: str, pad: str = "0 28px") -> str:
    return f'<tr><td bgcolor="#ffffff" style="background:#ffffff;padding:{pad}">{content}</td></tr>'


def _detail_rows(details: list[tuple[str, str]]) -> str:
    return "".join(
        f'<tr><td style="padding:7px 12px;color:{SOFT};font-size:14px;width:38%">{htmlmod.escape(k)}</td>'
        f'<td style="padding:7px 12px;color:{INK};font-size:14px;font-weight:700">{htmlmod.escape(v)}</td></tr>'
        for k, v in details
    )


def branded_html(
    subject: str,
    text: str,
    details: list[tuple[str, str]] | None = None,
) -> str:
    """The Virundhu email card: green header, greeting, message, details, a turmeric button, thanks and a quote.

    Built with tables, bgcolor attributes and inline styles so phone mail apps (Gmail, Outlook, Apple Mail) keep the
    colours. A line that is only a link becomes the button.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    paras = [p for p in paras if p not in ("- Virundhu", "Team Virundhu")]
    rows: list[str] = []
    marker = bool(details) and any(p.rstrip().endswith("details you gave us:") for p in paras)
    placed = False
    for para in paras:
        lines = para.split("\n")
        if len(lines) == 1 and URL_LINE.match(lines[0]):
            if details and not marker and not placed:
                # The table goes above the "Choose a plan:" style line that introduces the button.
                at = len(rows) - 1 if rows and paras[paras.index(para) - 1].rstrip().endswith(":") else len(rows)
                rows.insert(at, "__DETAILS__" + _detail_rows(details))
                placed = True
            url = htmlmod.escape(lines[0].strip(), quote=True)
            rows.append(
                _cell(
                    f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 22px"><tr>'
                    f'<td bgcolor="{TURMERIC}" style="background:{TURMERIC};border-radius:10px">'
                    f'<a href="{url}" style="display:inline-block;padding:14px 26px;color:{INK};font-weight:700;'
                    f'font-size:16px;text-decoration:none">{_button_label(url)}</a></td></tr></table>'
                )
            )
            continue
        safe = "<br>".join(htmlmod.escape(line) for line in lines)
        safe = re.sub(r"(https?://[^\s<]+)", rf'<a href="\1" style="color:{FOREST}">\1</a>', safe)
        big = lines[0].startswith(("Hi ", "Welcome", "Hello")) and len(lines) == 1
        style = f"margin:0 0 16px;font-size:{'18px;font-weight:700' if big else '15px'};line-height:1.6;color:{INK}"
        rows.append(_cell(f'<p style="{style}">{safe}</p>'))
        if details and para.rstrip().endswith("details you gave us:"):
            rows.append("__DETAILS__" + _detail_rows(details))
    if details and not marker and not placed:
        rows.append("__DETAILS__" + _detail_rows(details))
    if details:
        table = (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{CREAM}" '
            f'style="background:{CREAM};border-radius:12px;margin:0 0 18px">'
        )
        rows = [_cell(table + r[len("__DETAILS__") :] + "</table>") if r.startswith("__DETAILS__") else r for r in rows]
    site = settings.APP_URL.replace("https://", "").replace("http://", "")
    place = htmlmod.escape(settings.COMPANY_ADDRESS or "Coimbatore, Tamil Nadu")
    kind = email_kind(subject)
    headline, subline, accent, quote = KINDS[kind]
    if kind == "countdown":
        m = re.search(r"ends in (.+)$", subject)
        headline = headline.format(n=m.group(1) if m else "A few days")
        if "free trial" in subject.lower():
            headline = headline.replace("your plan", "your free trial")
    logo = f"{settings.APP_URL}/email-logo.png"
    header = (
        f'<tr><td bgcolor="{FOREST}" style="background:{FOREST};padding:20px 28px;border-radius:16px 16px 0 0">'
        f'<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'<td style="padding-right:12px"><img src="{logo}" width="44" height="44" alt="Virundhu" '
        f'style="display:block;border:0"></td>'
        f'<td><div style="color:{CREAM};font-size:24px;font-weight:700;line-height:1">Virundhu</div>'
        f'<div style="color:{TURMERIC};font-size:13px;margin-top:4px">Every guest, heard</div></td>'
        f"</tr></table></td></tr>"
        f'<tr><td bgcolor="{accent}" style="background:{accent};height:5px;line-height:5px;font-size:0">'
        "&nbsp;</td></tr>"
    )
    hero = ""
    if headline:
        hero = (
            f'<tr><td bgcolor="{CREAM}" style="background:{CREAM};padding:24px 28px;border-bottom:1px solid #efdcbf">'
            f'<div style="font-size:24px;line-height:1.25;font-weight:700;color:{FOREST}">'
            f"{htmlmod.escape(headline)}</div>"
            f'<div style="font-size:14px;color:{SOFT};margin-top:6px">{htmlmod.escape(subline)}</div></td></tr>'
        )
    closing = _cell(
        f'<p style="margin:8px 0 4px;font-size:15px;color:{INK}">Thank you so much,</p>'
        f'<p style="margin:0 0 18px;font-size:15px;font-weight:700;color:{FOREST}">Team Virundhu</p>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
        f'<td bgcolor="{FOREST}" style="background:{FOREST};border-radius:12px;padding:16px 18px">'
        f'<div style="font-size:26px;line-height:1;color:{TURMERIC};font-family:Georgia,serif">\u201c</div>'
        f'<div style="font-size:15px;line-height:1.5;color:{CREAM};font-family:Georgia,serif;font-style:italic">'
        f"{htmlmod.escape(quote)}</div></td></tr></table>",
        "0 28px 24px",
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light only"><meta name="supported-color-schemes" content="light">'
        f"<title>{htmlmod.escape(subject)}</title></head>"
        f'<body bgcolor="{CREAM}" style="margin:0;padding:0;background:{CREAM};font-family:Arial,Helvetica,sans-serif">'
        f'<div style="display:none;max-height:0;overflow:hidden">{htmlmod.escape(subline or subject)}</div>'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{CREAM}" '
        f'style="background:{CREAM}"><tr><td align="center" style="padding:20px 10px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#ffffff" '
        f'style="max-width:560px;background:#ffffff;border-radius:16px;border:1px solid #efdcbf">'
        + header
        + hero
        + _cell("", "22px 28px 0")
        + "".join(rows)
        + closing
        + f'<tr><td bgcolor="{CREAM}" style="background:{CREAM};padding:14px 28px;font-size:12px;color:{SOFT};'
        f'border-radius:0 0 16px 16px">Sent by Virundhu · {place} · {htmlmod.escape(site)}<br>Need help? Reply to '
        f"this email or use Quick help on the site.</td></tr></table></td></tr></table></body></html>"
    )


def send_email(
    to: list[str],
    subject: str,
    text: str,
    html: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
    details: list[tuple[str, str]] | None = None,
) -> bool:
    """Send one email to several recipients. Returns True when sent (or logged in development).

    Customer emails get the branded Virundhu design automatically; emails to the platform admin stay plain.
    """
    recipients = sorted({r.strip().lower() for r in to if r and "@" in r})
    if not recipients:
        return False
    internal = {settings.SUPERADMIN_EMAIL.lower(), settings.notify_email.lower(), settings.demo_requests_email.lower()}
    if html is None and not internal & set(recipients):
        html = branded_html(subject, text, details)
        if details:
            text = text.rstrip() + "\n\n" + "\n".join(f"{k}: {v}" for k, v in details)
        text = text.rstrip() + closing_text(subject)
    if not settings.SMTP_HOST:
        files = ", ".join(f[0] for f in attachments or [])
        logger.info("EMAIL (not sent, SMTP_HOST is empty) to=%s subject=%s %s\n%s", recipients, subject, files, text)
        _log_customer_email(recipients, f"Not sent (email isn't set up): {subject}", False)
        return True
    msg = EmailMessage()
    msg["From"] = sender()
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Reply-To"] = formataddr(("Virundhu", settings.CONTACT_EMAIL or parseaddr(sender())[1]))
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    for filename, data, mime in attachments or []:
        main, _, sub = mime.partition("/")
        msg.add_attachment(data, maintype=main, subtype=sub, filename=filename)
    try:
        helo = settings.SMTP_HELO or settings.APP_URL.split("//")[-1].split("/")[0].split(":")[0] or None
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20, local_hostname=helo) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
        ok = True
    except Exception:
        logger.exception("Email to %s failed", recipients)
        ok = False
    _log_customer_email(recipients, subject, ok)
    return ok


def _log_customer_email(recipients: list[str], subject: str, ok: bool) -> None:
    """Keep a record of every customer email in that restaurant's log (Admin console → Logs). Never raises."""
    if {settings.SUPERADMIN_EMAIL.lower(), settings.notify_email.lower(), settings.demo_requests_email.lower()} & set(
        recipients
    ):
        return
    try:
        from sqlalchemy import select

        from app.database import SessionLocal
        from app.models import Membership, Organization, User
        from app.services import activity

        with SessionLocal() as db:
            for to in recipients:
                row = db.execute(
                    select(Organization.id, Organization.name)
                    .join(Membership, Membership.organization_id == Organization.id)
                    .join(User, User.id == Membership.user_id)
                    .where(User.email == to)
                    .limit(1)
                ).first()
                activity.record(
                    db,
                    "email_sent" if ok else "email_failed",
                    org_id=row[0] if row else None,
                    restaurant=row[1] if row else None,
                    email=to,
                    detail=subject[:300],
                )
    except Exception:  # pragma: no cover - logging only
        logger.warning("Couldn't log the email to %s", recipients)
