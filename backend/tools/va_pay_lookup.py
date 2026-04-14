"""VA disability pay rate lookup tool - 2026 rates."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "va_pay_rates_2026.json"
_pay_data: dict | None = None

_DEPENDENT_STATUS_MAP = {
    "alone": "veteran_alone",
    "veteran_alone": "veteran_alone",
    "spouse": "with_spouse",
    "with_spouse": "with_spouse",
    "spouse_one_child": "with_spouse_and_one_child",
    "with_spouse_and_one_child": "with_spouse_and_one_child",
    "spouse_two_children": "with_spouse_and_two_children",
    "with_spouse_and_two_children": "with_spouse_and_two_children",
    "one_child": "veteran_alone_with_one_child",
    "veteran_alone_with_one_child": "veteran_alone_with_one_child",
}


def _load() -> dict:
    global _pay_data
    if _pay_data is None:
        with open(_DATA_PATH) as f:
            _pay_data = json.load(f)
    return _pay_data


def va_pay_lookup(combined_rating: int, dependent_status: str = "alone") -> dict:
    """
    Look up monthly VA disability pay for a given combined rating and dependent status.

    Args:
        combined_rating: Combined disability rating (10, 20, 30 ... 100).
        dependent_status: One of: 'alone', 'spouse', 'spouse_one_child',
                          'spouse_two_children', 'one_child'.

    Returns:
        dict with monthly pay, annual pay, and rate metadata.
    """
    data = _load()
    rating_key = str(combined_rating)
    status_key = _DEPENDENT_STATUS_MAP.get(dependent_status.lower(), "veteran_alone")
    rate_table = data.get(status_key, data["veteran_alone"])

    monthly = rate_table.get(rating_key)
    if monthly is None:
        # Find nearest valid rating
        valid_ratings = sorted([int(k) for k in rate_table.keys()])
        nearest = min(valid_ratings, key=lambda x: abs(x - combined_rating))
        monthly = rate_table.get(str(nearest), 0.0)
        note = f"No exact rate for {combined_rating}%. Using nearest available: {nearest}%."
    else:
        note = None

    return {
        "combined_rating": combined_rating,
        "dependent_status": dependent_status,
        "rate_table_used": status_key,
        "monthly_pay_usd": monthly,
        "annual_pay_usd": round(monthly * 12, 2) if monthly else 0.0,
        "note": note,
        "source": "VA.gov 2026 Disability Compensation Rates",
    }


def calculate_pay_impact(
    current_rating: int,
    potential_rating: int,
    dependent_status: str = "alone",
) -> dict:
    """
    Calculate the monthly and annual pay difference between current and potential ratings.

    Args:
        current_rating: Current combined rating.
        potential_rating: Potential combined rating after successful appeal.
        dependent_status: Veteran's dependent status.

    Returns:
        dict with current pay, potential pay, and dollar impact.
    """
    current = va_pay_lookup(current_rating, dependent_status)
    potential = va_pay_lookup(potential_rating, dependent_status)

    monthly_diff = (potential["monthly_pay_usd"] or 0) - (current["monthly_pay_usd"] or 0)
    annual_diff = monthly_diff * 12

    return {
        "current_rating": current_rating,
        "potential_rating": potential_rating,
        "dependent_status": dependent_status,
        "current_monthly_usd": current["monthly_pay_usd"],
        "potential_monthly_usd": potential["monthly_pay_usd"],
        "monthly_increase_usd": round(monthly_diff, 2),
        "annual_increase_usd": round(annual_diff, 2),
        "lifetime_note": (
            f"A {potential_rating - current_rating}% rating increase is worth "
            f"${monthly_diff:,.2f}/month (${annual_diff:,.2f}/year) in additional benefits."
        ),
    }
