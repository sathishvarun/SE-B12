"""Create the platform admin. Safe to run many times.

Run:  python -m app.seed

The old sample restaurant is removed unless SEED_DEMO_RESTAURANT=true (used only by the automated tests).
"""

import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.config import settings
from app.database import SessionLocal
from app.demo_data import seed_demo_reviews
from app.models import AlertRule, Membership, Organization, Outlet, Subscription, User
from app.services.dates import today_local

logger = logging.getLogger("seed")

DEMO_ORG = {"name": "Vaasam Biryani House", "slug": "vaasam-biryani-house", "city": "Chennai"}
DEMO_MANAGER_EMAIL = "rspuram@virundhu.local"
DEMO_OUTLETS = [("Anna Nagar", "Chennai"), ("RS Puram", "Coimbatore"), ("KK Nagar", "Madurai")]


def _get_or_create_user(db: Session, email: str, password: str, name: str, superadmin: bool) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user:
        return user
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=name,
        is_active=True,
        is_verified=True,
        is_superadmin=superadmin,
    )
    db.add(user)
    db.flush()
    logger.info("Created user %s", email)
    return user


def ensure_admin_email(db: Session) -> None:
    """If SUPERADMIN_EMAIL changed, move the existing admin login to it (the password stays the same)."""
    wanted = settings.SUPERADMIN_EMAIL.lower()
    current = db.scalar(select(User).where(User.is_superadmin.is_(True)).order_by(User.id))
    if current and current.email != wanted:
        taken = db.scalar(select(User).where(User.email == wanted))
        if taken is None:
            logger.info("Admin sign-in email changed from %s to %s (password unchanged)", current.email, wanted)
            current.email = wanted
            db.flush()
        else:
            logger.warning(
                "SUPERADMIN_EMAIL %s already belongs to another account: delete that account first "
                "(python -m app.delete_account %s), then restart.",
                wanted,
                wanted,
            )


def remove_demo(db: Session) -> None:
    """Delete the sample restaurant and its sample logins (database cascades remove its reviews)."""
    n = db.execute(delete(Organization).where(Organization.is_demo.is_(True))).rowcount
    demo_emails = [settings.DEMO_EMAIL.lower(), DEMO_MANAGER_EMAIL]
    db.execute(delete(User).where(User.email.in_(demo_emails), User.is_superadmin.is_(False)))
    db.commit()
    if n:
        logger.info("Removed the sample restaurant")


def seed(db: Session) -> None:
    """Create the platform admin. Customers create their own restaurant by registering."""
    ensure_admin_email(db)
    admin = _get_or_create_user(db, settings.SUPERADMIN_EMAIL, settings.SUPERADMIN_PASSWORD, "Virundhu Admin", True)
    # The platform admin is never inside a restaurant; they use the Admin console.
    for m in db.scalars(select(Membership).where(Membership.user_id == admin.id)):
        db.delete(m)
    db.commit()
    if os.getenv("SEED_DEMO_RESTAURANT", "").lower() != "true":
        remove_demo(db)
        return

    org = db.scalar(select(Organization).where(Organization.slug == DEMO_ORG["slug"]))
    if not org:
        org = Organization(
            **DEMO_ORG,
            plan="growth",
            is_demo=True,
            reply_tone="warm",
            reply_signature="- Team Vaasam",
            trial_ends_at=datetime.now(UTC) + timedelta(days=3650),
        )
        db.add(org)
        db.flush()
        for name, city in DEMO_OUTLETS:
            db.add(Outlet(organization_id=org.id, name=name, area=name, city=city))
        db.add(Subscription(organization_id=org.id, plan="growth", status="active"))
        logger.info("Created demo organization %s", org.name)

    demo = _get_or_create_user(db, settings.DEMO_EMAIL, settings.DEMO_PASSWORD, "Priya R", False)
    demo.full_name = "Priya R"
    # Demo owner: sees the whole demo restaurant (read-only).
    demo_m = db.scalar(select(Membership).where(Membership.user_id == demo.id, Membership.organization_id == org.id))
    if demo_m is None:
        db.add(Membership(user_id=demo.id, organization_id=org.id, role="owner"))
    else:
        demo_m.role, demo_m.outlet_ids = "owner", None
    # Demo outlet manager: sees ONLY the RS Puram outlet (shows how outlet staff access works).
    rs_puram = db.scalar(select(Outlet).where(Outlet.organization_id == org.id, Outlet.name == "RS Puram"))
    manager = _get_or_create_user(db, DEMO_MANAGER_EMAIL, settings.DEMO_PASSWORD, "Karthik S", False)
    manager.full_name = "Karthik S"
    if rs_puram and not db.scalar(select(Membership).where(Membership.user_id == manager.id)):
        db.add(Membership(user_id=manager.id, organization_id=org.id, role="manager", outlet_ids=[rs_puram.id]))
    if not db.scalar(select(AlertRule).where(AlertRule.organization_id == org.id)):
        db.add(AlertRule(organization_id=org.id, recipients=[settings.DEMO_EMAIL], min_urgency="high"))
    db.commit()
    added = seed_demo_reviews(db, org.id, today_local())
    if added:
        logger.info("Added %d sample reviews to the demo restaurant", added)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with SessionLocal() as db:
        seed(db)
    logger.info("Seed complete. Admin login: %s", settings.SUPERADMIN_EMAIL)


if __name__ == "__main__":
    main()
