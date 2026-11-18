"""Realistic sample reviews for the demo restaurant (fictional brand: Vaasam Biryani House).

Each template carries the analysis Virundhu would return, so the demo needs no AI calls.
Fields: text, rating, sentiment, category, urgency, language, summary, reply, platforms, weight, outlet_bias
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Outlet, Review, ReviewAnalysis

SIGN = "- Team Vaasam"
ANY = ("google", "zomato", "swiggy")
DELIVERY = ("zomato", "swiggy")

TEMPLATES: list[dict] = [
    # ---------- English ----------
    dict(
        text="Biryani was amazing, packing also neat. Will order again!",
        rating=5,
        sentiment="positive",
        category="food_quality",
        urgency="low",
        language="english",
        summary="Loved the biryani and the neat packing.",
        reply=f"Thank you so much! We're happy the biryani and packing made your day. See you again soon. {SIGN}",
        platforms=ANY,
        weight=6,
    ),
    dict(
        text="Ordered at 8pm, came at 9:10. Food fully cold. Very bad.",
        rating=1,
        sentiment="negative",
        category="delivery",
        urgency="high",
        language="english",
        summary="Order arrived 70 minutes late and the food was cold.",
        reply=f"We're really sorry your order reached late and cold. Please DM us your order ID so we can make "
        f"it right. {SIGN}",
        platforms=DELIVERY,
        weight=3,
        outlet_bias="Anna Nagar",
    ),
    dict(
        text="Staff were very polite and the service was quick even on a busy Sunday.",
        rating=5,
        sentiment="positive",
        category="staff",
        urgency="low",
        language="english",
        summary="Polite staff and quick service on a busy Sunday.",
        reply=f"Thank you! We'll pass your kind words to the team. {SIGN}",
        platforms=("google",),
        weight=4,
    ),
    dict(
        text="Parotta was hard and the salna was too salty this time.",
        rating=2,
        sentiment="negative",
        category="food_quality",
        urgency="medium",
        language="english",
        summary="Parotta was hard and the salna too salty.",
        reply=f"Sorry the parotta and salna weren't up to the mark. We've shared this with our kitchen team. {SIGN}",
        platforms=ANY,
        weight=2,
    ),
    dict(
        text="They charged for a water bottle we never ordered. Please check your bills.",
        rating=2,
        sentiment="negative",
        category="price",
        urgency="medium",
        language="english",
        summary="Was billed for a water bottle that was not ordered.",
        reply=f"Sorry about the billing mistake. Please DM us your bill number and we'll check it right away. {SIGN}",
        platforms=("google",),
        weight=2,
        outlet_bias="RS Puram",
    ),
    dict(
        text="Found a small insect in the curry. Very disappointed.",
        rating=1,
        sentiment="negative",
        category="hygiene",
        urgency="high",
        language="english",
        summary="Found an insect in the curry.",
        reply=f"We're truly sorry. This is not our standard and we are checking the kitchen today. Please DM us "
        f"your order ID so we can reach you. {SIGN}",
        platforms=ANY,
        weight=1,
    ),
    dict(
        text="Food was good but the app kept failing at the payment step.",
        rating=3,
        sentiment="neutral",
        category="app",
        urgency="medium",
        language="english",
        summary="Liked the food but the app payment kept failing.",
        reply=f"Thanks for letting us know about the payment issue. We're looking into it. {SIGN}",
        platforms=DELIVERY,
        weight=1,
    ),
    dict(
        text="The container leaked and gravy spilled all over the bag.",
        rating=2,
        sentiment="negative",
        category="packaging",
        urgency="medium",
        language="english",
        summary="Container leaked and gravy spilled in the bag.",
        reply=f"Sorry about the leak. We're changing our gravy containers this week. {SIGN}",
        platforms=DELIVERY,
        weight=2,
    ),
    dict(
        text="Average taste, nothing special for the price.",
        rating=3,
        sentiment="neutral",
        category="price",
        urgency="low",
        language="english",
        summary="Found the taste average for the price.",
        reply=f"Thank you for the honest feedback. We'll keep working to give you more value. {SIGN}",
        platforms=ANY,
        weight=2,
    ),
    dict(
        text="The manager was rude when I asked for a fresh plate.",
        rating=1,
        sentiment="negative",
        category="staff",
        urgency="high",
        language="english",
        summary="Manager was rude when asked for a fresh plate.",
        reply=f"We're sorry for how you were treated. This isn't how we want our guests to feel. Please DM us "
        f"so we can talk. {SIGN}",
        platforms=("google",),
        weight=1,
        outlet_bias="KK Nagar",
    ),
    dict(
        text="Best chicken 65 in town. Crispy and hot every time.",
        rating=5,
        sentiment="positive",
        category="food_quality",
        urgency="low",
        language="english",
        summary="Loved the crispy, hot chicken 65.",
        reply=f"That's lovely to hear! Our chicken 65 team will be thrilled. {SIGN}",
        platforms=ANY,
        weight=5,
    ),
    dict(
        text="Delivery partner was courteous and right on time.",
        rating=5,
        sentiment="positive",
        category="delivery",
        urgency="low",
        language="english",
        summary="Delivery was on time and courteous.",
        reply=f"Thank you! Glad your order reached you on time. {SIGN}",
        platforms=DELIVERY,
        weight=3,
    ),
    # ---------- Tanglish ----------
    dict(
        text="Saapadu nalla irundhuchu but bill la extra charge pottanga",
        rating=2,
        sentiment="negative",
        category="price",
        urgency="medium",
        language="tanglish",
        summary="Liked the food but was charged extra on the bill.",
        reply=f"Ungal feedback-ku nandri! Bill la extra charge pathi sorry. Bill number DM pannunga, check panni "
        f"solrom. {SIGN}",
        platforms=("google",),
        weight=2,
        outlet_bias="RS Puram",
    ),
    dict(
        text="Chicken la mudi irundhuchu. Very disgusting, need refund.",
        rating=1,
        sentiment="negative",
        category="hygiene",
        urgency="high",
        language="tanglish",
        summary="Found a hair in the chicken and is asking for a refund.",
        reply=f"Idhu nadandhadhuku romba sorry. Udane kitchen la check pannrom. Ungal order ID DM pannunga, naanga "
        f"contact pannrom. {SIGN}",
        platforms=DELIVERY,
        weight=1,
    ),
    dict(
        text="Biryani semma taste, quantity um nalla irundhuchu",
        rating=5,
        sentiment="positive",
        category="food_quality",
        urgency="low",
        language="tanglish",
        summary="Great biryani taste and good quantity.",
        reply=f"Romba nandri! Marubadiyum vaanga. {SIGN}",
        platforms=ANY,
        weight=5,
    ),
    dict(
        text="Delivery romba late, 1 hour aachu, food ellam cold",
        rating=1,
        sentiment="negative",
        category="delivery",
        urgency="high",
        language="tanglish",
        summary="Delivery took an hour and the food was cold.",
        reply=f"Late delivery-ku romba sorry. Ungal order ID DM pannunga, idha sari pannrom. {SIGN}",
        platforms=DELIVERY,
        weight=2,
        outlet_bias="Anna Nagar",
    ),
    dict(
        text="Staff romba friendly, service fast ah irundhuchu",
        rating=5,
        sentiment="positive",
        category="staff",
        urgency="low",
        language="tanglish",
        summary="Friendly staff and fast service.",
        reply=f"Ungal anbana vaarthaikku nandri! Team kitta solrom. {SIGN}",
        platforms=("google",),
        weight=3,
    ),
    dict(
        text="Portion konjam kammi, taste ok",
        rating=3,
        sentiment="neutral",
        category="food_quality",
        urgency="low",
        language="tanglish",
        summary="Taste was fine but the portion was small.",
        reply=f"Feedback-ku nandri. Portion size pathi kitchen team kitta pesurom. {SIGN}",
        platforms=ANY,
        weight=2,
    ),
    dict(
        text="Parcel la gravy leak aagiduchu, bag full ah spoil",
        rating=2,
        sentiment="negative",
        category="packaging",
        urgency="medium",
        language="tanglish",
        summary="Gravy leaked and spoiled the whole bag.",
        reply=f"Sorry! Packing-a improve pannrom. Adutha order la idhu nadakkaadhu. {SIGN}",
        platforms=DELIVERY,
        weight=2,
    ),
    dict(
        text="Saapta aprom vaanthi vandhuchu, kitchen hygiene check pannunga",
        rating=1,
        sentiment="negative",
        category="hygiene",
        urgency="high",
        language="tanglish",
        summary="Vomited after eating and asks the kitchen to check hygiene.",
        reply=f"Idhu kekka romba varutham. Ungal udal nalam mukkiyam. Order ID DM pannunga, udane pesurom. {SIGN}",
        platforms=ANY,
        weight=1,
        outlet_bias="KK Nagar",
    ),
    # ---------- Tamil ----------
    dict(
        text="பிரியாணி ரொம்ப சுவையா இருந்தது. ஸ்டாஃப் எல்லாரும் அன்பா பேசினாங்க.",
        rating=5,
        sentiment="positive",
        category="food_quality",
        urgency="low",
        language="tamil",
        summary="Loved the biryani and found the staff friendly.",
        reply=f"உங்கள் அன்பான வார்த்தைகளுக்கு மிக்க நன்றி! மீண்டும் வாருங்கள். {SIGN}",
        platforms=("google",),
        weight=4,
    ),
    dict(
        text="சாப்பாடு நல்லா இருந்தது, ஆனால் டெலிவரி ரொம்ப தாமதம்.",
        rating=3,
        sentiment="neutral",
        category="delivery",
        urgency="medium",
        language="tamil",
        summary="Food was good but delivery was very late.",
        reply=f"தாமதத்திற்கு மன்னிக்கவும். டெலிவரி நேரத்தை மேம்படுத்துகிறோம். {SIGN}",
        platforms=DELIVERY,
        weight=2,
        outlet_bias="Anna Nagar",
    ),
    dict(
        text="விலை கொஞ்சம் அதிகம், ஆனால் சுவை அருமை.",
        rating=4,
        sentiment="positive",
        category="price",
        urgency="low",
        language="tamil",
        summary="Price is a little high but the taste is excellent.",
        reply=f"உங்கள் கருத்துக்கு நன்றி! சுவை பிடித்ததில் மகிழ்ச்சி. {SIGN}",
        platforms=ANY,
        weight=2,
    ),
    dict(
        text="சாப்பாட்டில் முடி இருந்தது. இது சரியில்லை.",
        rating=1,
        sentiment="negative",
        category="hygiene",
        urgency="high",
        language="tamil",
        summary="Found a hair in the food.",
        reply=f"இதற்கு மிகவும் வருந்துகிறோம். உடனே சமையலறையை சரிபார்க்கிறோம். உங்கள் ஆர்டர் எண்ணை DM செய்யுங்கள். {SIGN}",
        platforms=ANY,
        weight=1,
    ),
    dict(
        text="பார்சல் நன்றாக பேக் செய்யப்பட்டிருந்தது. நன்றி!",
        rating=5,
        sentiment="positive",
        category="packaging",
        urgency="low",
        language="tamil",
        summary="Parcel was packed well.",
        reply=f"மிக்க நன்றி! மீண்டும் ஆர்டர் செய்யுங்கள். {SIGN}",
        platforms=DELIVERY,
        weight=3,
    ),
]


def seed_demo_reviews(db: Session, org_id: int, today: date, count: int = 160) -> int:
    """Insert sample reviews spread over the last 8 weeks. Skips if the org already has reviews."""
    if db.scalar(select(func.count(Review.id)).where(Review.organization_id == org_id)):
        return 0
    outlets = {o.name: o.id for o in db.scalars(select(Outlet).where(Outlet.organization_id == org_id))}
    if not outlets:
        return 0
    rng = random.Random(2026)  # noqa: S311 - same demo data every time, not security
    weights = [t["weight"] for t in TEMPLATES]
    for i in range(count):
        t = rng.choices(TEMPLATES, weights=weights)[0]
        # recent weeks a little busier; a delivery problem building up at Anna Nagar
        age = min(int(rng.triangular(0, 56, 4)), 55)
        bias = t.get("outlet_bias")
        outlet = bias if bias and rng.random() < 0.7 and bias in outlets else rng.choice(list(outlets))
        review_date = today - timedelta(days=age)
        pending = age <= 3 or (t["urgency"] == "high" and age <= 6)
        review = Review(
            organization_id=org_id,
            outlet_id=outlets[outlet],
            external_id=f"DEMO-{i + 1:04d}",
            platform=rng.choice(t["platforms"]),
            rating=t["rating"],
            review_date=review_date,
            review_text=t["text"],
            analysis_status="analyzed",
            is_sample=True,
            workflow_status="new" if pending else ("replied" if rng.random() < 0.85 else "ignored"),
            final_reply=None if pending else t["reply"],
        )
        db.add(review)
        db.flush()
        db.add(
            ReviewAnalysis(
                review_id=review.id,
                sentiment=t["sentiment"],
                category=t["category"],
                urgency=t["urgency"],
                language=t["language"],
                summary=t["summary"],
                suggested_reply=t["reply"],
                status="analyzed",
                model_used="demo",
                cost_inr=Decimal("0"),
                safety_override=False,
            )
        )
    db.commit()
    return count
