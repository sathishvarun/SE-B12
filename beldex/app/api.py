"""FastAPI backend: sign-in, the Beldex agent, usage tracking and the admin API.

Run:  uvicorn app.api:app --reload --port 8000      Docs: http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import json
import re
import threading
from collections import Counter, defaultdict
from datetime import timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.news_crew import load_digest, run_crew
from app.config import ROOT, settings
from app.db import (Activity, KnowledgeRun, LoginSession, QueryLog, SessionLocal, User, get_db,
                    init_db, now)
from app.metrics import measure, server_snapshot
from app.rag.chain import ask
from app.rag.knowledge import kb
from app import voice
from app.security import Caller, admin_only, check_password, current, hash_password, make_token

app = FastAPI(title="Beldex AI API", version="1.0.0",
              description="Bilingual Beldex knowledge agent with sign-in and admin analytics.")
ONLINE_MINUTES = 5


# ---------------------------------------------------------------- startup
@app.on_event("startup")
def startup() -> None:
    init_db()
    with SessionLocal() as db:
        has_admin = db.scalar(select(func.count()).select_from(User).where(User.role == "admin"))
        if not has_admin and settings.admin_password:
            db.add(User(name="Administrator", username="admin", email=settings.admin_email,
                        password_hash=hash_password(settings.admin_password), role="admin"))
            db.commit()
            print(f"[startup] admin account created for {settings.admin_email}")
    threading.Thread(target=kb.ensure, daemon=True).start()  # warm the index


def _client(request: Request) -> tuple[str, str]:
    ip = request.headers.get("x-client-ip") or request.headers.get("x-forwarded-for", "").split(",")[0] \
        or (request.client.host if request.client else "")
    return ip.strip(), (request.headers.get("x-client-ua") or request.headers.get("user-agent", ""))[:300]


def _log(db: Session, user_id: int | None, action: str, detail: str = "") -> None:
    db.add(Activity(user_id=user_id, action=action, detail=detail[:500]))


def _user_out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "first_name": u.name.split(" ")[0], "username": u.username,
            "email": u.email, "role": u.role, "lang": u.lang, "active": u.active}


PASSWORD_RULE = "Password must be at least 8 characters and include at least one letter and one number."


def _password_ok(pw: str) -> bool:
    return len(pw) >= 8 and re.search(r"[A-Za-z]", pw) is not None and re.search(r"\d", pw) is not None


# ---------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(default="", max_length=60)
    email: str = Field(max_length=200)
    password: str = Field(max_length=128)
    lang: str = "en"

    @field_validator("first_name", "last_name")
    @classmethod
    def _clean(cls, v: str) -> str:
        return " ".join(v.split())


class LoginIn(BaseModel):
    login: str
    password: str
    as_role: str = "user"  # which tab the person used: "user" or "admin"


def _start_session(db: Session, user: User, request: Request) -> dict:
    ip, ua = _client(request)
    sess = LoginSession(user_id=user.id, ip=ip, user_agent=ua)
    user.last_login = now()
    db.add(sess)
    db.flush()
    _log(db, user.id, "sign_in", f"{ip} · {ua[:80]}")
    db.commit()
    return {"token": make_token(user, sess.id), "user": _user_out(user)}


@app.post("/auth/register")
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not settings.allow_signup:
        raise HTTPException(403, "Sign-up is closed. Ask the admin for an account.")
    if not body.first_name:
        raise HTTPException(422, "Please enter your first name.")
    if not _password_ok(body.password):
        raise HTTPException(422, PASSWORD_RULE)
    email = _clean_email(body.email)
    if not email:
        raise HTTPException(422, BAD_EMAIL)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "This email is already registered. Please sign in instead.")
    base = re.sub(r"[^a-z0-9_.-]", "", email.split("@")[0]) or "user"
    username, n = base, 1
    while db.scalar(select(User).where(User.username == username)):
        n += 1
        username = f"{base}{n}"
    user = User(name=f"{body.first_name} {body.last_name}".strip(), username=username, email=email,
                password_hash=hash_password(body.password), lang="ta" if body.lang == "ta" else "en")
    db.add(user)
    db.flush()
    _log(db, user.id, "sign_up")
    return _start_session(db, user, request)


BAD_EMAIL = "Enter a real email address, like name@gmail.com."


def _clean_email(raw: str) -> str | None:
    """Same rules for the live check and for sign-up, so the form never says 'Looks good' and then fails."""
    try:
        return validate_email(raw.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        return None


@app.get("/auth/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    """Live check while the person types on the sign-up form."""
    e = _clean_email(email) or ""
    valid = bool(e)
    taken = valid and db.scalar(select(User.id).where(User.email == e)) is not None
    return {"valid": valid, "available": valid and not taken}


@app.post("/auth/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    key = body.login.strip().lower()
    user = db.scalar(select(User).where(or_(func.lower(User.username) == key, User.email == key)))
    if not user or not check_password(body.password, user.password_hash):
        _log(db, user.id if user else None, "sign_in_failed", key)
        db.commit()
        raise HTTPException(401, "Wrong email or password")
    if not user.active:
        raise HTTPException(403, "This account is suspended")
    if body.as_role == "admin" and user.role != "admin":
        _log(db, user.id, "admin_denied")
        db.commit()
        raise HTTPException(403, "This account does not have admin access")
    return _start_session(db, user, request)


@app.post("/auth/logout")
def logout(caller: Caller = Depends(current), db: Session = Depends(get_db)):
    if caller.session:
        s = db.get(LoginSession, caller.session.id)
        s.ended_at = now()
    _log(db, caller.user.id, "sign_out")
    db.commit()
    return {"ok": True}


@app.get("/me")
def me(caller: Caller = Depends(current)):
    return _user_out(caller.user)


class PrefIn(BaseModel):
    lang: str


@app.post("/me/lang")
def set_lang(body: PrefIn, caller: Caller = Depends(current), db: Session = Depends(get_db)):
    u = db.get(User, caller.user.id)
    u.lang = "ta" if body.lang == "ta" else "en"
    db.commit()
    return _user_out(u)


# ---------------------------------------------------------------- the agent
class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    lang: str = "en"
    via: str = "text"


@app.post("/chat")
def chat(body: AskIn, caller: Caller = Depends(current), db: Session = Depends(get_db)):
    with measure() as use:
        ans = ask(body.question, body.lang)
    row = QueryLog(user_id=caller.user.id, session_id=caller.session.id if caller.session else None,
                   question=body.question, answer=ans.text, lang=ans.lang,
                   sources_json=json.dumps(ans.sources, ensure_ascii=False), found=ans.found, mode=ans.mode,
                   prompt_tokens=ans.prompt_tokens, completion_tokens=ans.completion_tokens,
                   cost_usd=ans.cost_usd, latency_ms=use.latency_ms, cpu_ms=use.cpu_ms, mem_mb=use.mem_mb,
                   via="voice" if body.via == "voice" else "text")
    db.add(row)
    db.commit()
    return {"id": row.id, "answer": ans.text, "lang": ans.lang, "sources": ans.sources, "found": ans.found,
            "mode": ans.mode, "steps": ans.steps, "follow_ups": ans.follow_ups,
            "usage": {"prompt_tokens": ans.prompt_tokens, "completion_tokens": ans.completion_tokens,
                      "cost_usd": ans.cost_usd, "latency_ms": use.latency_ms, "cpu_ms": use.cpu_ms}}


class FeedbackIn(BaseModel):
    value: int = Field(ge=-1, le=1)


@app.post("/chat/{qid}/feedback")
def feedback(qid: int, body: FeedbackIn, caller: Caller = Depends(current), db: Session = Depends(get_db)):
    row = db.get(QueryLog, qid)
    if not row or row.user_id != caller.user.id:
        raise HTTPException(404, "Not found")
    row.feedback = body.value
    db.commit()
    return {"ok": True}


@app.get("/history")
def history(caller: Caller = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(select(QueryLog).where(QueryLog.user_id == caller.user.id)
                      .order_by(QueryLog.id.desc()).limit(50)).all()
    return [{"id": r.id, "at": r.created_at.isoformat(), "question": r.question, "answer": r.answer,
             "lang": r.lang, "sources": json.loads(r.sources_json), "found": r.found} for r in rows]


class ActivityIn(BaseModel):
    action: str = Field(max_length=40)
    detail: str = ""


@app.post("/activity")
def activity(body: ActivityIn, caller: Caller = Depends(current), db: Session = Depends(get_db)):
    _log(db, caller.user.id, body.action, body.detail)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- voice
@app.get("/voice/status")
def voice_status(caller: Caller = Depends(current)):
    return {"server": voice.available(), "stt_model": voice.STT_MODEL, "tts_model": voice.TTS_MODEL}


@app.post("/voice/transcribe")
async def voice_transcribe(request: Request, lang: str = "en", secs: float = 0,
                           caller: Caller = Depends(current), db: Session = Depends(get_db)):
    if not voice.available():
        raise HTTPException(503, "Server voice is not set up (no OpenAI key). The browser's own voice input will be used.")
    audio = await request.body()
    if not audio or len(audio) > voice.MAX_AUDIO_BYTES:
        raise HTTPException(413 if audio else 400, "Recording is empty or too long (max about 5 minutes).")
    try:
        text = voice.transcribe(audio, request.headers.get("content-type", "audio/webm"), "ta" if lang == "ta" else "en")
    except Exception as exc:
        raise HTTPException(502, f"Could not understand the recording: {str(exc)[:160]}")
    _log(db, caller.user.id, "voice_in", f"{secs:.0f}s · {text[:120]}")
    db.commit()
    return {"text": text}


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    lang: str = "en"


@app.post("/voice/speak")
def voice_speak(body: SpeakIn, caller: Caller = Depends(current), db: Session = Depends(get_db)):
    if not voice.available():
        raise HTTPException(503, "Server voice is not set up (no OpenAI key).")
    try:
        audio, cached = voice.speak(body.text, "ta" if body.lang == "ta" else "en")
    except Exception as exc:
        raise HTTPException(502, f"Could not create the audio: {str(exc)[:160]}")
    if not cached:
        _log(db, caller.user.id, "voice_out", f"{len(voice.speakable(body.text))} characters")
        db.commit()
    return Response(content=audio, media_type="audio/mpeg")


# ---------------------------------------------------------------- knowledge + news (all users)
@app.get("/news")
def news(caller: Caller = Depends(current)):
    return load_digest()


@app.get("/kb/sources")
def kb_sources(caller: Caller = Depends(current)):
    return {"backend": kb.backend, "chunks": len(kb.chunks), "sources": kb.sources()}


@app.get("/health")
def health():
    return {"ok": True, "llm": settings.has_llm, "search": kb.backend or "starting"}


# ---------------------------------------------------------------- admin
def _online(s: LoginSession | None) -> bool:
    return bool(s and not s.ended_at and s.last_seen > now() - timedelta(minutes=ONLINE_MINUTES))


@app.get("/admin/overview")
def admin_overview(days: int = 14, _: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    since = now() - timedelta(days=days)
    users = db.scalars(select(User)).all()
    sessions = db.scalars(select(LoginSession).where(LoginSession.started_at >= since)).all()
    queries = db.scalars(select(QueryLog).where(QueryLog.created_at >= since)).all()
    online = {s.user_id for s in sessions if _online(s)}

    by_day = defaultdict(lambda: {"questions": 0, "tokens": 0, "minutes": 0.0, "users": set(), "cost": 0.0})
    for q in queries:
        d = by_day[q.created_at.date().isoformat()]
        d["questions"] += 1
        d["tokens"] += q.prompt_tokens + q.completion_tokens
        d["cost"] += q.cost_usd
        d["users"].add(q.user_id)
    for s in sessions:
        d = by_day[s.started_at.date().isoformat()]
        d["minutes"] += s.seconds / 60
        d["users"].add(s.user_id)
    series = [{"day": k, "questions": v["questions"], "tokens": v["tokens"], "minutes": round(v["minutes"], 1),
               "active_users": len(v["users"]), "cost_usd": round(v["cost"], 4)} for k, v in sorted(by_day.items())]

    n = len(queries) or 1
    topics = Counter()
    for q in queries:
        for src in json.loads(q.sources_json)[:1]:
            topics[src["title"]] += 1
    hours = [0] * 24
    for q in queries:
        hours[(q.created_at + timedelta(hours=5, minutes=30)).hour] += 1
    names = {u.id: u.name for u in users}
    online_people = sorted({names.get(s.user_id, "?") for s in sessions if _online(s)})
    feed = db.execute(select(Activity, User.name).outerjoin(User, User.id == Activity.user_id)
                      .order_by(Activity.id.desc()).limit(8)).all()
    return {
        "top_topics": [{"topic": t, "questions": c} for t, c in topics.most_common(6)],
        "by_hour_ist": hours,
        "online_people": online_people,
        "feed": [{"at": a.created_at.isoformat(), "who": nm or "Someone", "action": a.action, "detail": a.detail[:80]}
                 for a, nm in feed],
        "kpis": {
            "users": len(users), "admins": sum(u.role == "admin" for u in users), "online": len(online),
            "new_users": sum(u.created_at >= since for u in users),
            "questions": len(queries), "answered_pct": round(100 * sum(q.found for q in queries) / n),
            "avg_session_min": round(sum(s.seconds for s in sessions) / 60 / (len(sessions) or 1), 1),
            "total_hours": round(sum(s.seconds for s in sessions) / 3600, 1),
            "tokens": sum(q.prompt_tokens + q.completion_tokens for q in queries),
            "cost_usd": round(sum(q.cost_usd for q in queries), 4),
            "avg_latency_ms": int(sum(q.latency_ms for q in queries) / n),
            "voice_pct": round(100 * sum(q.via == "voice" for q in queries) / n),
            "helpful_pct": round(100 * sum(q.feedback == 1 for q in queries)
                                 / (sum(q.feedback is not None for q in queries) or 1)),
        },
        "series": series,
        "languages": dict(Counter("Tamil" if q.lang == "ta" else "English" for q in queries)),
        "unanswered": [{"question": q.question, "at": q.created_at.isoformat()} for q in queries if not q.found][-15:],
        "server": server_snapshot(),
        "knowledge": {"backend": kb.backend, "chunks": len(kb.chunks), "sources": len(kb.sources())},
        "llm": {"configured": settings.has_llm, "model": settings.llm_model},
        "voice": {"server": voice.available(), "stt": voice.STT_MODEL, "tts": voice.TTS_MODEL},
    }


@app.get("/admin/users")
def admin_users(_: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    out = []
    for u in db.scalars(select(User).order_by(User.created_at.desc())).all():
        ss = db.scalars(select(LoginSession).where(LoginSession.user_id == u.id)
                        .order_by(LoginSession.started_at.desc())).all()
        qs = db.scalars(select(QueryLog).where(QueryLog.user_id == u.id)).all()
        last = ss[0] if ss else None
        out.append({**_user_out(u), "created_at": u.created_at.isoformat(),
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "status": "Suspended" if not u.active else ("Online" if _online(last) else "Offline"),
                    "sessions": len(ss), "minutes": round(sum(s.seconds for s in ss) / 60, 1),
                    "questions": len(qs), "tokens": sum(q.prompt_tokens + q.completion_tokens for q in qs),
                    "cost_usd": round(sum(q.cost_usd for q in qs), 4),
                    "cpu_ms": sum(q.cpu_ms for q in qs),
                    "last_ip": last.ip if last else "", "device": last.user_agent if last else "",
                    "spark": [sum(1 for q in qs if (now().date() - q.created_at.date()).days == d) for d in range(6, -1, -1)]})
    return out


@app.get("/admin/users/{uid}")
def admin_user(uid: int, _: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "No such user")
    ss = db.scalars(select(LoginSession).where(LoginSession.user_id == uid).order_by(LoginSession.id.desc()).limit(50)).all()
    qs = db.scalars(select(QueryLog).where(QueryLog.user_id == uid).order_by(QueryLog.id.desc()).limit(100)).all()
    acts = db.scalars(select(Activity).where(Activity.user_id == uid).order_by(Activity.id.desc()).limit(100)).all()
    return {
        "user": _user_out(u),
        "sessions": [{"id": s.id, "started_at": s.started_at.isoformat(), "last_seen": s.last_seen.isoformat(),
                      "ended": bool(s.ended_at), "minutes": round(s.seconds / 60, 1), "ip": s.ip,
                      "device": s.user_agent, "online": _online(s)} for s in ss],
        "queries": [{"id": q.id, "at": q.created_at.isoformat(), "question": q.question, "answer": q.answer,
                     "lang": q.lang, "found": q.found, "mode": q.mode, "sources": json.loads(q.sources_json),
                     "tokens": q.prompt_tokens + q.completion_tokens, "cost_usd": q.cost_usd,
                     "latency_ms": q.latency_ms, "cpu_ms": q.cpu_ms, "mem_mb": q.mem_mb,
                     "feedback": q.feedback, "via": q.via} for q in qs],
        "activity": [{"at": a.created_at.isoformat(), "action": a.action, "detail": a.detail} for a in acts],
    }


class UserPatch(BaseModel):
    active: bool | None = None
    role: str | None = None


@app.patch("/admin/users/{uid}")
def admin_patch_user(uid: int, body: UserPatch, caller: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "No such user")
    if u.id == caller.user.id and (body.active is False or body.role == "user"):
        raise HTTPException(400, "You cannot suspend or demote your own account")
    if body.active is not None:
        u.active = body.active
    if body.role in {"user", "admin"}:
        u.role = body.role
    _log(db, caller.user.id, "admin_update_user", f"{u.username}: active={u.active} role={u.role}")
    db.commit()
    return _user_out(u)


@app.get("/admin/queries")
def admin_queries(limit: int = 200, _: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.execute(select(QueryLog, User.username).join(User, User.id == QueryLog.user_id)
                      .order_by(QueryLog.id.desc()).limit(min(limit, 1000))).all()
    return [{"id": q.id, "at": q.created_at.isoformat(), "user": name, "question": q.question,
             "lang": q.lang, "found": q.found, "mode": q.mode, "tokens": q.prompt_tokens + q.completion_tokens,
             "cost_usd": q.cost_usd, "latency_ms": q.latency_ms, "cpu_ms": q.cpu_ms, "mem_mb": q.mem_mb,
             "sources": len(json.loads(q.sources_json)), "feedback": q.feedback, "via": q.via} for q, name in rows]


@app.get("/admin/activity")
def admin_activity(limit: int = 200, _: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.execute(select(Activity, User.username).outerjoin(User, User.id == Activity.user_id)
                      .order_by(Activity.id.desc()).limit(min(limit, 1000))).all()
    return [{"at": a.created_at.isoformat(), "user": name or "—", "action": a.action, "detail": a.detail}
            for a, name in rows]


def _refresh_job(run_id: int) -> None:
    from app.rag.crawler import refresh
    lines: list[str] = []
    with SessionLocal() as db:
        run = db.get(KnowledgeRun, run_id)
        try:
            res = refresh(log=lines.append)
            run.status, run.pages, run.chunks = "done", res["pages"] + res["posts"], res["chunks"]
            run_crew()
            lines.append("News digest rebuilt.")
        except Exception as exc:
            run.status = "failed"
            lines.append(f"Error: {exc}")
        run.finished_at, run.message = now(), "\n".join(lines[-60:])
        db.commit()


@app.post("/admin/kb/refresh")
def admin_refresh(tasks: BackgroundTasks, caller: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    if db.scalar(select(KnowledgeRun).where(KnowledgeRun.status == "running")):
        raise HTTPException(409, "A refresh is already running")
    run = KnowledgeRun()
    db.add(run)
    _log(db, caller.user.id, "kb_refresh")
    db.commit()
    tasks.add_task(_refresh_job, run.id)
    return {"run_id": run.id}


@app.get("/admin/kb/runs")
def admin_runs(_: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    rows = db.scalars(select(KnowledgeRun).order_by(KnowledgeRun.id.desc()).limit(20)).all()
    return [{"id": r.id, "started_at": r.started_at.isoformat(), "status": r.status, "pages": r.pages,
             "chunks": r.chunks, "message": r.message} for r in rows]


@app.post("/admin/news/run")
def admin_news(caller: Caller = Depends(admin_only), db: Session = Depends(get_db)):
    _log(db, caller.user.id, "news_digest")
    db.commit()
    return run_crew()


# ---------------------------------------------------------------- web app (Beldex AI front end)
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/index.html")


app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")
