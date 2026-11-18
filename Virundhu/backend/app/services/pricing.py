"""Virundhu pricing in one place: the price is worked out from the number of outlets and how many months are paid.

- More outlets = lower price per outlet (volume tiers), so big chains (e.g. 100+ branches) get a much better rate.
- Longer periods = a discount, and 9 and 12 months add free bonus months.
- Prices are in rupees and include GST. Change the tables below to change pricing everywhere
  (website, billing page, Dodo and Razorpay checkout, payment checks).
"""

from dataclasses import asdict, dataclass

# (lowest outlet count in the tier, price per outlet per month in rupees, tier name)
OUTLET_TIERS: list[tuple[int, int, str]] = [
    (1, 1499, "Single outlet"),
    (2, 1199, "Small chain"),
    (6, 949, "Growing chain"),
    (21, 799, "Large chain"),
    (51, 649, "Enterprise chain"),
]

# months paid -> (discount percent, free bonus months)
DURATIONS: dict[int, tuple[int, int]] = {
    1: (0, 0),
    3: (5, 0),
    6: (10, 0),
    9: (10, 1),
    12: (15, 2),
}

MAX_OUTLETS = 500
REVIEWS_PER_OUTLET = 500  # monthly AI reading allowance per paid outlet
DAYS_PER_MONTH = 30.44


class PricingError(ValueError):
    """Asked for something we don't sell."""


@dataclass(frozen=True)
class Quote:
    outlets: int
    months: int
    bonus_months: int
    tier: str
    plan: str  # starter | growth | chain, used for limits and the admin view
    per_outlet_month: int  # rupees, before the duration discount
    discount_percent: int
    list_total: int  # rupees without any discount (single-outlet price x outlets x months)
    total: int  # rupees to pay
    you_save: int
    effective_per_outlet_month: int  # what one outlet really costs per month, bonus months included
    access_days: int

    def as_dict(self) -> dict:
        return asdict(self)


def tier_for(outlets: int) -> tuple[int, str]:
    price, name = OUTLET_TIERS[0][1], OUTLET_TIERS[0][2]
    for low, p, n in OUTLET_TIERS:
        if outlets >= low:
            price, name = p, n
    return price, name


def plan_for(outlets: int) -> str:
    return "starter" if outlets <= 1 else "growth" if outlets <= 5 else "chain"


def quote(outlets: int, months: int) -> Quote:
    if months not in DURATIONS:
        raise PricingError("Choose 1, 3, 6, 9 or 12 months.")
    if not 1 <= outlets <= MAX_OUTLETS:
        raise PricingError(f"Choose between 1 and {MAX_OUTLETS} outlets. For more, talk to us.")
    per_outlet, tier = tier_for(outlets)
    discount, bonus = DURATIONS[months]
    total = round(per_outlet * outlets * months * (100 - discount) / 100)
    list_total = OUTLET_TIERS[0][1] * outlets * (months + bonus)
    return Quote(
        outlets=outlets,
        months=months,
        bonus_months=bonus,
        tier=tier,
        plan=plan_for(outlets),
        per_outlet_month=per_outlet,
        discount_percent=discount,
        list_total=list_total,
        total=total,
        you_save=max(0, list_total - total),
        effective_per_outlet_month=round(total / outlets / (months + bonus)),
        access_days=round((months + bonus) * DAYS_PER_MONTH),
    )


def table() -> dict:
    """Everything the website needs to show the calculator, so the browser never invents prices."""
    return {
        "tiers": [{"from_outlets": low, "per_outlet_month": p, "name": n} for low, p, n in OUTLET_TIERS],
        "durations": [{"months": m, "discount_percent": d, "bonus_months": b} for m, (d, b) in DURATIONS.items()],
        "max_outlets": MAX_OUTLETS,
        "reviews_per_outlet": REVIEWS_PER_OUTLET,
    }
