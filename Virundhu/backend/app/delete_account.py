"""Delete one account completely: its restaurant(s) where it's the only member, all reviews and settings, and the login.

    cd backend && .venv/bin/python -m app.delete_account someone@gmail.com

Shows what will go and asks you to type DELETE first. The admin login can't be deleted this way.
"""

import sys

from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Membership, Organization, Review, User
from app.services import activity


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    email = sys.argv[1].strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            local = email.split("@")[0][:5]
            near = list(db.scalars(select(User.email).where(User.email.ilike(f"%{local}%"))))
            print(f"No account with the email {email}.")
            if near:
                print("Did you mean one of these?\n  " + "\n  ".join(near))
            return 1
        if user.is_superadmin:
            print("That's the admin login. It can't be deleted here.")
            return 1
        orgs = list(db.scalars(select(Organization).join(Membership).where(Membership.user_id == user.id)))
        to_delete = []
        for o in orgs:
            members = db.scalar(select(func.count(Membership.id)).where(Membership.organization_id == o.id)) or 0
            reviews = db.scalar(select(func.count(Review.id)).where(Review.organization_id == o.id)) or 0
            if members == 1:
                to_delete.append(o)
            print(
                f"- Restaurant '{o.name}': {reviews} reviews, {members} member(s)"
                + ("  -> will be DELETED" if members == 1 else "  -> kept (other people use it); only access removed")
            )
        print(f"- Login {user.email} ({user.full_name})  -> will be DELETED")
        if input("Type DELETE to delete this for good: ").strip() != "DELETE":
            print("Cancelled. Nothing was deleted.")
            return 1
        for o in to_delete:
            activity.record(
                db,
                "account_deleted",
                org_id=o.id,
                restaurant=o.name,
                email=user.email,
                detail="Deleted by the platform owner from the command line",
                commit=False,
            )
            db.execute(delete(Organization).where(Organization.id == o.id))
        db.execute(delete(Membership).where(Membership.user_id == user.id))
        db.execute(delete(User).where(User.id == user.id))
        db.commit()
        print(f"Deleted {user.email} and {len(to_delete)} restaurant(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
