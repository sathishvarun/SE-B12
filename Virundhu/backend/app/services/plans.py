"""Plan limits in one place. Paid restaurants get limits from the number of outlets they paid for."""

from app.services.pricing import REVIEWS_PER_OUTLET

PLAN_LIMITS: dict[str, dict[str, int]] = {
    "trial": {"reviews_per_month": 150, "outlets": 3, "seats": 3},
    "starter": {"reviews_per_month": 500, "outlets": 1, "seats": 3},
    "growth": {"reviews_per_month": 2500, "outlets": 5, "seats": 5},
    "chain": {"reviews_per_month": 1_000_000, "outlets": 1000, "seats": 100},
}


def limits(plan: str) -> dict[str, int]:
    """Limits for a plan (unknown plans get trial limits)."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["trial"])


def limits_for(org: object) -> dict[str, int]:
    """Limits for one restaurant: paid outlets decide outlets and monthly reviews; otherwise the plan's defaults."""
    plan = getattr(org, "plan", "trial")
    base = dict(limits(plan))
    paid = getattr(org, "paid_outlets", None)
    if plan != "trial" and paid:
        base["outlets"] = paid
        base["reviews_per_month"] = paid * REVIEWS_PER_OUTLET
    return base
