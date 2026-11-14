"""Promote a user to admin.

Usage (from backend/):
    python -m app.scripts.make_admin <email>
"""

import argparse
import logging
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User

logger = logging.getLogger("make_admin")


def make_admin(email: str) -> bool:
    """Set is_admin=True for the user with this email. Returns False if not found."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            logger.error("No user found with email %s", email)
            return False
        if user.is_admin:
            logger.info("User %s is already an admin", user.email)
            return True
        user.is_admin = True
        db.commit()
        logger.info("User %s is now an admin", user.email)
        return True


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Grant admin rights to a user.")
    parser.add_argument("email", help="Email of an existing user")
    args = parser.parse_args()
    sys.exit(0 if make_admin(args.email) else 1)


if __name__ == "__main__":
    main()
