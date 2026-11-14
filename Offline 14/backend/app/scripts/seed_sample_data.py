"""Fill one account with realistic sample CRM data, using every field.

Creates tags, contacts, leads (every source and status, one converted), deals
(every stage), tasks (every priority, done/pending, linked to contact/lead/deal
or nothing, overdue/today/upcoming) and two small attachments.
All names, phone numbers and emails are made up (emails use example.com).

Usage (from backend/):
    python -m app.scripts.seed_sample_data                       # demo@example.com
    python -m app.scripts.seed_sample_data --email you@example.com
    python -m app.scripts.seed_sample_data --email demo@example.com --password 'MyDemoPass123'

If the account doesn't exist it is created (free plan). If no --password is given
for a new account, a random one is generated and shown once in the log.
An account that already has contacts is left alone, so running it twice is safe.
"""

import argparse
import io
import logging
import secrets
import struct
import sys
import zlib
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database import SessionLocal
from app.models import (
    Attachment,
    Contact,
    Deal,
    DealStage,
    Lead,
    LeadSource,
    LeadStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    Tag,
    Task,
    TaskPriority,
    TaskStatus,
    User,
)
from app.services.storage import get_storage

logger = logging.getLogger("seed_sample_data")

TODAY = date.today()
NOW = datetime.now(UTC)

TAG_NAMES = ["VIP", "Chennai", "Wholesale", "Repeat buyer", "Needs follow-up"]

# name, email, phone, company, address, notes, tags
CONTACTS = [
    (
        "Priya Raman",
        "priya.raman@example.com",
        "+91 98400 11223",
        "Raman Textiles",
        "12 Ranganathan St, T. Nagar, Chennai 600017",
        "Buys cotton sarees in bulk before every festival season.",
        ["VIP", "Chennai", "Wholesale"],
    ),
    (
        "Arjun Mehta",
        "arjun.mehta@example.com",
        "+91 99870 44556",
        "Mehta Electronics",
        "45 Lamington Rd, Grant Road, Mumbai 400007",
        "Prefers WhatsApp. Pays within 15 days.",
        ["Repeat buyer"],
    ),
    (
        "Kavya Subramanian",
        "kavya.s@example.com",
        "+91 94440 77889",
        "Kavya Organics",
        "8 Avinashi Rd, Peelamedu, Coimbatore 641004",
        "Small organic food brand, growing fast.",
        ["Needs follow-up"],
    ),
    (
        "Rahul Verma",
        "rahul.verma@example.com",
        "+91 98110 22334",
        "Verma Logistics",
        "Plot 21, Sector 18, Gurugram 122015",
        "Decision maker for the fleet software budget.",
        ["VIP"],
    ),
    (
        "Fatima Khan",
        "fatima.khan@example.com",
        "+91 90000 55667",
        "Khan Interiors",
        "3-6-112 Himayatnagar, Hyderabad 500029",
        "Met at the Hyderabad home expo.",
        [],
    ),
    (
        "Sanjay Iyer",
        "sanjay.iyer@example.com",
        "+91 98450 66778",
        "Iyer & Sons Hardware",
        "22 Avenue Rd, Chickpet, Bengaluru 560053",
        "Family business, third generation.",
        ["Wholesale", "Repeat buyer"],
    ),
    (
        "Meera Nair",
        "meera.nair@example.com",
        "+91 94950 88990",
        "Nair Spices",
        "Jew Town Rd, Mattancherry, Kochi 682002",
        "Exports to the Gulf. Wants GST invoices.",
        ["VIP"],
    ),
    (
        "Vikram Singh",
        "vikram.singh@example.com",
        "+91 98290 12121",
        "Singh Motors",
        "MI Rd, Jaipur 302001",
        "Asked for a demo of the Pro plan.",
        ["Needs follow-up"],
    ),
    (
        "Anitha Krishnan",
        "anitha.k@example.com",
        "+91 98410 34343",
        "Anitha Bakes",
        "5 Besant Ave, Adyar, Chennai 600020",
        "Home bakery, orders cake boxes monthly.",
        ["Chennai"],
    ),
    (
        "Deepak Joshi",
        "deepak.joshi@example.com",
        "+91 98220 56565",
        "Joshi Printing Press",
        "Shaniwar Peth, Pune 411030",
        "Needs quotes by email only.",
        [],
    ),
]

# name, email, phone, company, source, status, notes
LEADS = [
    (
        "Lakshmi Prasad",
        "lakshmi.p@example.com",
        "+91 98401 10101",
        "Prasad Silks",
        LeadSource.WEBSITE,
        LeadStatus.NEW,
        "Filled the contact form asking about bulk pricing.",
    ),
    (
        "Rohan Das",
        "rohan.das@example.com",
        "+91 98300 20202",
        "Das Tea Traders",
        LeadSource.REFERRAL,
        LeadStatus.CONTACTED,
        "Referred by Arjun Mehta. Called once, call back next week.",
    ),
    (
        "Sneha Pillai",
        "sneha.pillai@example.com",
        "+91 94470 30303",
        "Pillai Ayurveda",
        LeadSource.SOCIAL,
        LeadStatus.QUALIFIED,
        "Found us on Instagram. Budget confirmed.",
    ),
    (
        "Imran Sheikh",
        "imran.sheikh@example.com",
        "+91 98200 40404",
        "Sheikh Leather Works",
        LeadSource.OTHER,
        LeadStatus.LOST,
        "Went with a cheaper local vendor.",
    ),
    (
        "Divya Reddy",
        "divya.reddy@example.com",
        "+91 99490 50505",
        "Reddy Pharma Distributors",
        LeadSource.WEBSITE,
        LeadStatus.QUALIFIED,
        "Wants a call with the owner before deciding.",
    ),
    (
        "Karthik Raja",
        "karthik.raja@example.com",
        "+91 98940 60606",
        "Raja Fresh Farms",
        LeadSource.SOCIAL,
        LeadStatus.NEW,
        "Commented on our LinkedIn post.",
    ),
    (
        "Pooja Agarwal",
        "pooja.agarwal@example.com",
        "+91 98310 70707",
        "Agarwal Sweets",
        LeadSource.REFERRAL,
        LeadStatus.CONTACTED,
        "Sent the brochure by email.",
    ),
]

# title, contact index, value, currency, stage, expected close (days from today), notes
DEALS = [
    (
        "Diwali saree order",
        0,
        "250000",
        "INR",
        DealStage.NEGOTIATION,
        10,
        "Discussing a 5% discount for orders above 2 lakh.",
    ),
    (
        "Showroom POS upgrade",
        1,
        "85000",
        "INR",
        DealStage.PROPOSAL,
        21,
        "Proposal sent with 3 options.",
    ),
    (
        "Organic store shelf space",
        2,
        "40000",
        "INR",
        DealStage.PROSPECT,
        30,
        "First call done, needs a sample box.",
    ),
    ("Fleet tracking software", 3, "320000", "INR", DealStage.WON, -5, "Signed annual contract."),
    (
        "Office interiors",
        4,
        "150000",
        "INR",
        DealStage.LOST,
        -12,
        "Client postponed the project to next year.",
    ),
    (
        "Hardware bulk supply",
        5,
        "60000",
        "INR",
        DealStage.PROSPECT,
        -3,
        "Expected close date already passed: follow up!",
    ),
    (
        "Spice export pack",
        6,
        "4500",
        "USD",
        DealStage.NEGOTIATION,
        14,
        "Priced in USD for the Dubai buyer.",
    ),
    ("Showroom signage", 7, "25000", "INR", DealStage.WON, -20, "Paid in full."),
    ("Monthly cake boxes", 8, "12000", "INR", DealStage.PROPOSAL, 7, "Recurring monthly order."),
]

# title, description, due (days from today or None), priority, done?,
# link: ("contact" | "lead" | "deal", index into that list) or None
TASKS = [
    (
        "Call Priya about the discount",
        "Confirm the final discount and delivery date.",
        0,
        TaskPriority.HIGH,
        False,
        ("deal", 0),
    ),
    (
        "Send POS proposal follow-up",
        "Ask if they had time to review the 3 options.",
        2,
        TaskPriority.MEDIUM,
        False,
        ("deal", 1),
    ),
    ("Ship sample box to Kavya", None, -2, TaskPriority.HIGH, False, ("contact", 2)),
    (
        "Call back Rohan Das",
        "He asked us to call after Tuesday.",
        5,
        TaskPriority.MEDIUM,
        False,
        ("lead", 1),
    ),
    ("Book meeting with Divya's owner", None, 3, TaskPriority.HIGH, False, ("lead", 4)),
    (
        "Send onboarding guide to Verma Logistics",
        "Contract signed; share the setup guide.",
        -6,
        TaskPriority.LOW,
        True,
        ("deal", 3),
    ),
    (
        "Ask Fatima for feedback",
        "Why did they postpone? Note it for next year.",
        -10,
        TaskPriority.LOW,
        True,
        ("contact", 4),
    ),
    (
        "Chase hardware supply decision",
        "Close date has passed.",
        -1,
        TaskPriority.HIGH,
        False,
        ("deal", 5),
    ),
    (
        "Prepare GST invoice template",
        "For export customers like Nair Spices.",
        9,
        TaskPriority.MEDIUM,
        False,
        ("contact", 6),
    ),
    (
        "Plan next month's Instagram posts",
        "Most social leads come from Instagram.",
        12,
        TaskPriority.LOW,
        False,
        None,
    ),
    ("Weekly pipeline review", None, 0, TaskPriority.MEDIUM, False, None),
    (
        "Update price list",
        "New supplier prices from 1st of next month.",
        -4,
        TaskPriority.MEDIUM,
        True,
        None,
    ),
]


def _sample_pdf() -> bytes:
    """A one-page PDF that says "Sample quotation" (enough to open in any viewer)."""
    text = b"BT /F1 18 Tf 30 70 Td (Sample quotation) Tj ET"
    return (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        + b"4 0 obj<</Length "
        + str(len(text)).encode()
        + b">>stream\n"
        + text
        + b"\nendstream endobj\n"
        + b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"trailer<</Root 1 0 R>>\n%%EOF\n"
    )


def _sample_png() -> bytes:
    """A 1x1 violet PNG, built by hand so it is always valid."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1 pixel, 8-bit RGB
    pixel = zlib.compress(b"\x00\x7c\x3a\xed")  # filter byte + one violet pixel
    return (
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", pixel) + chunk(b"IEND", b"")
    )


def _days(offset: int | None) -> date | None:
    """Date `offset` days from today (None stays None)."""
    return None if offset is None else TODAY + timedelta(days=offset)


def _get_or_create_user(db: Session, email: str, password: str | None, name: str) -> User:
    """Return the account, creating it (free plan, verified) if it doesn't exist."""
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        logger.info("Using existing account %s", email)
        return user

    if not password:
        password = secrets.token_urlsafe(12)
        logger.info(
            "Generated password for %s: %s  (save it, it won't be shown again)", email, password
        )
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=name,
        is_verified=True,
    )
    user.subscription = Subscription(plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE)
    db.add(user)
    db.flush()
    logger.info("Created account %s", email)
    return user


def seed(email: str, password: str | None, name: str) -> bool:
    """
    Create the sample data for one account.

    Args:
        email: Account to fill (created if missing)
        password: Password for a new account (random if not given)
        name: Full name for a new account

    Returns:
        True if data was created, False if the account already had contacts
    """
    email = email.strip().lower()
    with SessionLocal() as db:
        user = _get_or_create_user(db, email, password, name)
        existing = db.scalar(select(func.count(Contact.id)).where(Contact.user_id == user.id))
        if existing:
            logger.warning(
                "%s already has %s contacts; not adding sample data twice.", email, existing
            )
            db.rollback()
            return False

        tags = {tag_name: Tag(user_id=user.id, name=tag_name) for tag_name in TAG_NAMES}
        db.add_all(tags.values())

        contacts = [
            Contact(
                user_id=user.id,
                name=c_name,
                email=c_email,
                phone=phone,
                company=company,
                address=address,
                notes=notes,
                tags=[tags[t] for t in tag_list],
            )
            for c_name, c_email, phone, company, address, notes, tag_list in CONTACTS
        ]
        db.add_all(contacts)
        db.flush()

        leads = [
            Lead(
                user_id=user.id,
                name=l_name,
                email=l_email,
                phone=phone,
                company=company,
                source=source,
                status=status,
                notes=notes,
            )
            for l_name, l_email, phone, company, source, status, notes in LEADS
        ]
        # One converted lead, linked to the contact it became (Anitha Krishnan).
        leads.append(
            Lead(
                user_id=user.id,
                name="Anitha Krishnan",
                email="anitha.k@example.com",
                phone="+91 98410 34343",
                company="Anitha Bakes",
                source=LeadSource.REFERRAL,
                status=LeadStatus.CONVERTED,
                notes="Converted after the tasting session.",
                converted_contact_id=contacts[8].id,
            )
        )
        db.add_all(leads)

        deals: list[Deal] = []
        positions: dict[DealStage, int] = {}
        for title, contact_idx, value, currency, stage, close_in, notes in DEALS:
            closed = stage in (DealStage.WON, DealStage.LOST)
            deals.append(
                Deal(
                    user_id=user.id,
                    contact_id=contacts[contact_idx].id,
                    title=title,
                    value=Decimal(value),
                    currency=currency,
                    stage=stage,
                    position=positions.get(stage, 0),
                    expected_close_date=_days(close_in),
                    notes=notes,
                    closed_at=NOW + timedelta(days=close_in) if closed else None,
                )
            )
            positions[stage] = positions.get(stage, 0) + 1
        db.add_all(deals)
        db.flush()

        targets = {"contact": contacts, "lead": leads, "deal": deals}
        for title, description, due_in, priority, done, link in TASKS:
            task = Task(
                user_id=user.id,
                title=title,
                description=description,
                due_date=_days(due_in),
                priority=priority,
                status=TaskStatus.DONE if done else TaskStatus.PENDING,
                reminder_sent=done,
                completed_at=NOW - timedelta(days=1) if done else None,
            )
            if link is not None:
                kind, index = link
                setattr(task, f"{kind}_id", targets[kind][index].id)
            db.add(task)

        storage = get_storage()
        for filename, content_type, data, contact_id, deal_id in [
            ("Quotation-Raman-Textiles.pdf", "application/pdf", _sample_pdf(), None, deals[0].id),
            ("Shop-photo.png", "image/png", _sample_png(), contacts[0].id, None),
        ]:
            ext = filename.rsplit(".", 1)[1]
            storage_path, size = storage.save(user.id, io.BytesIO(data), ext)
            db.add(
                Attachment(
                    user_id=user.id,
                    contact_id=contact_id,
                    deal_id=deal_id,
                    filename=filename,
                    content_type=content_type,
                    size_bytes=size,
                    storage_path=storage_path,
                )
            )

        db.commit()
        logger.info(
            "Added %s tags, %s contacts, %s leads, %s deals, %s tasks and 2 files for %s",
            len(tags),
            len(contacts),
            len(leads),
            len(deals),
            len(TASKS),
            email,
        )
        return True


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Add sample CRM data to an account.")
    parser.add_argument(
        "--email", default="demo@example.com", help="Account to fill (created if missing)"
    )
    parser.add_argument(
        "--password", default=None, help="Password for a new account (random if omitted)"
    )
    parser.add_argument("--name", default="Demo Seller", help="Full name for a new account")
    args = parser.parse_args()
    sys.exit(0 if seed(args.email, args.password, args.name) else 1)


if __name__ == "__main__":
    main()
