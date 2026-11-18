"""Fictional restaurant 'Annapoorna Mess' for the demo videos (not a real brand)."""
import requests, sys, uuid
from datetime import UTC, datetime, timedelta
sys.path.insert(0, "/home/claude/virundhu/backend")
from app.database import SessionLocal
from app.models import Organization, Outlet, Review, ReviewAnalysis
from app.services import alerts
from sqlalchemy import select
A = "http://localhost:8450"
email = f"kumar.demo{uuid.uuid4().hex[:4]}@example.com"
r = requests.post(A + "/api/v1/auth/register", json={"full_name": "Kumar", "organization_name": "Annapoorna Mess",
    "city": "Coimbatore", "email": email, "password": "Demo#Pass123", "accept_terms": True, "phone": "9876543210", "outlets": 3})
r.raise_for_status(); tok = r.json()["access_token"]; org_id = r.json()["user"]["organization"]["id"]
h = {"Authorization": f"Bearer {tok}"}
ids = {}
for name, area, mgr in (("RS Puram", "DB Road", "Ravi"), ("Gandhipuram", "Cross Cut Road", "Kala"), ("Peelamedu", "Avinashi Road", "Selvam")):
    o = requests.post(A + "/api/v1/outlets", json={"name": name, "area": area, "city": "Coimbatore", "district": "Coimbatore", "manager_name": mgr, "manager_phone": "98765 0000" + str(len(ids) + 1)}, headers=h).json()
    ids[name] = o["id"]
REV = [
    ("RS Puram", "zomato", 1, "Chicken biryani la mudi irundhuchu. Very disgusting, want refund.", "negative", "hygiene", "high", "tanglish", "Hair found in the chicken biryani; guest wants a refund.", "We're truly sorry about this. This is not the standard we hold ourselves to. Please share your order number so we can make it right, and we are checking with our kitchen team today."),
    ("Gandhipuram", "swiggy", 2, "Delivery 1 hour late, food was cold. Parotta was hard.", "negative", "delivery", "medium", "english", "Late delivery and cold, hard parotta.", "Sorry your food arrived late and cold. That's not how it should reach you. We're working with our delivery team on timings; please give us another chance."),
    ("Peelamedu", "google", 5, "Semma taste! Meals ellam super, staff romba friendly.", "positive", "food_quality", "low", "tanglish", "Loved the meals and the friendly staff.", "Romba nandri! So happy you enjoyed the meals. See you again soon!"),
    ("RS Puram", "google", 4, "Good food, slightly crowded at lunch. Sambar was excellent.", "positive", "food_quality", "low", "english", "Good food and excellent sambar; crowded at lunch.", "Thank you! Glad you liked the sambar. We're adding seating for the lunch rush."),
    ("Gandhipuram", "zomato", 3, "Taste ok but portion size reduced compared to last time.", "neutral", "price", "medium", "english", "Taste fine but smaller portions than before.", "Thank you for the honest feedback. We'll check our portion sizes with the kitchen."),
    ("Peelamedu", "direct", 1, "Saambar la poochi irundhuchu. Very bad experience.", "negative", "hygiene", "high", "tanglish", "Insect found in the sambar.", "We're very sorry about this. It is not acceptable, and we are checking the kitchen today. Please call us so we can make it right."),
    ("RS Puram", "swiggy", 5, "Best ghee roast in Coimbatore. Packing also neat.", "positive", "packaging", "low", "english", "Loved the ghee roast and neat packing.", "Thank you so much! Glad the ghee roast reached you hot and neat."),
    ("Gandhipuram", "google", 2, "Staff was rude when I asked for extra chutney.", "negative", "staff", "medium", "english", "Staff was rude about extra chutney.", "We're sorry about how you were treated. We've spoken to the team; please visit again and ask for the manager."),
]
with SessionLocal() as db:
    now = datetime.now(UTC)
    for i, (out, plat, rating, text, sent, cat, urg, lang, summ, reply) in enumerate(REV):
        rv = Review(organization_id=org_id, outlet_id=ids[out], external_id=f"demo-{org_id}-{i}", platform=plat, rating=rating,
                    review_date=(now - timedelta(days=i % 4)).date(), review_text=text, analysis_status="analyzed", workflow_status="new")
        db.add(rv); db.flush()
        an = ReviewAnalysis(review_id=rv.id, sentiment=sent, category=cat, urgency=urg, language=lang, summary=summ, suggested_reply=reply, status="analyzed", model_used="demo")
        db.add(an); db.flush()
        if urg == "high":
            alerts.alert_for_review(db, rv, an)
    db.commit()
print(email)
