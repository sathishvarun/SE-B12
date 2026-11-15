"""Fill the database with DEMO users, sessions and questions so the admin dashboard has something to show.

    python scripts/seed_demo.py          # adds demo data (all demo accounts use the password demo1234)
    python scripts/seed_demo.py --clear  # removes the demo accounts again

Never run this on a database with real customers unless you want demo rows mixed in.
"""
import json
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import Activity, LoginSession, QueryLog, SessionLocal, User, init_db, now  # noqa: E402
from app.rag.chain import ask  # noqa: E402
from app.security import hash_password  # noqa: E402

PEOPLE = [("Priya K", "priya_k", "ta"), ("Arun M", "arun.m", "en"), ("Kavya R", "kavya_r", "ta"),
          ("Rahul D", "rahul_dev", "en"), ("Meena S", "meena.s", "ta"), ("Vikram P", "vikram_p", "en")]
QUESTIONS = ["How did Beldex start?", "What do I need to run a masternode?", "What is BNS?",
             "What happened with the BSC bridge?", "Where can I trade BDX?", "What changed in the Obscura hardfork?",
             "What is BelNet?", "Tell me about BChat", "What is on the 2026 roadmap?", "Who founded Beldex?",
             "What is the price of bitcoin tomorrow?"]
DEVICES = ["Android · Chrome", "iPhone · Safari", "Windows · Edge", "macOS · Chrome"]


def clear(db):
    for u in db.query(User).filter(User.email.like("%@demo.local")).all():
        for model in (QueryLog, LoginSession, Activity):
            db.query(model).filter(model.user_id == u.id).delete()
        db.delete(u)
    db.commit()


def main():
    init_db()
    random.seed(7)
    with SessionLocal() as db:
        clear(db)
        if "--clear" in sys.argv:
            print("Demo data removed.")
            return
        cache = {q: ask(q, "en") for q in QUESTIONS}
        for name, username, lang in PEOPLE:
            u = User(name=name, username=username, email=f"{username}@demo.local", lang=lang,
                     password_hash=hash_password("demo1234"),
                     created_at=now() - timedelta(days=random.randint(10, 20)))
            db.add(u)
            db.flush()
            for d in range(random.randint(3, 9)):
                start = now() - timedelta(days=random.randint(0, 13), hours=random.randint(0, 12))
                s = LoginSession(user_id=u.id, started_at=start, ip=f"49.37.{random.randint(1, 250)}.{random.randint(1, 250)}",
                                 user_agent=random.choice(DEVICES))
                s.last_seen = start + timedelta(minutes=random.randint(4, 45))
                s.ended_at = s.last_seen if random.random() < 0.7 else None
                db.add(s)
                db.flush()
                db.add(Activity(user_id=u.id, action="sign_in", created_at=start, detail=f"{s.ip} · {s.user_agent}"))
                for _ in range(random.randint(1, 5)):
                    q = random.choice(QUESTIONS)
                    a = cache[q]
                    p, c = random.randint(900, 2200), random.randint(120, 420)
                    db.add(QueryLog(user_id=u.id, session_id=s.id, question=q, answer=a.text, lang=lang,
                                    created_at=start + timedelta(minutes=random.randint(1, 30)),
                                    sources_json=json.dumps(a.sources), found=a.found, mode="llm",
                                    prompt_tokens=p if a.found else 0, completion_tokens=c if a.found else 0,
                                    cost_usd=round(p / 1e6 * 0.15 + c / 1e6 * 0.6, 6) if a.found else 0,
                                    latency_ms=random.randint(1400, 4200), cpu_ms=random.randint(20, 120),
                                    mem_mb=round(random.uniform(310, 380), 1),
                                    feedback=random.choice([1, 1, 1, None, -1]),
                                    via=random.choice(["text", "text", "voice"])))
            u.last_login = max((x.started_at for x in db.query(LoginSession).filter(LoginSession.user_id == u.id)),
                               default=None)
        db.commit()
    print(f"Added {len(PEOPLE)} demo users (password: demo1234).")


if __name__ == "__main__":
    main()
