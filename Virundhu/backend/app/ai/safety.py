"""Food-safety safety net: can only RAISE urgency to high, never lower it."""

import re

from app.ai.schemas import ReviewAnalysisOut

HIGH_RISK_PATTERNS = [
    r"food\s*poison",
    r"vomit",
    r"diarr",
    r"hospital",
    r"\bhair\b",
    r"cockroach",
    r"insect",
    r"\bworms?\b",
    r"\bstale\b",
    r"fungus",
    r"expired",
    r"\bbug\b",
    r"vaanthi",
    r"vomiting",
    r"puchi",
    r"karappan",
    r"\bmudi\b",
    "வாந்தி",
    "பூச்சி",
    "கரப்பான்",
    "முடி",
]
_RISK = re.compile("|".join(HIGH_RISK_PATTERNS), re.IGNORECASE)


def has_food_safety_risk(text: str) -> bool:
    """True when the review mentions a food-safety problem."""
    return bool(_RISK.search(text or ""))


def apply_safety_net(text: str, result: ReviewAnalysisOut) -> tuple[ReviewAnalysisOut, bool]:
    """Force urgency=high for food-safety reviews. Returns (result, overridden)."""
    if has_food_safety_risk(text) and result.urgency != "high":
        return result.model_copy(update={"urgency": "high"}), True
    return result, False
