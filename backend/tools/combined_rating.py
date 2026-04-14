"""VA combined ratings calculator using whole-person math (38 CFR Part 4)."""

from __future__ import annotations


def calculate_combined_rating(ratings: list[int]) -> dict:
    """
    Calculate VA combined disability rating using whole-person math.

    The VA does NOT add ratings. It applies each rating to the remaining
    whole person in descending order:
        combined = 1 - ((1 - r1) * (1 - r2) * ... * (1 - rN))
    Final result is rounded to the nearest 10 (5 rounds up).

    Args:
        ratings: List of individual disability ratings (0-100 integers).

    Returns:
        dict with keys: raw_decimal, raw_percent, combined_rating, ratings_used
    """
    if not ratings:
        return {"raw_decimal": 0.0, "raw_percent": 0.0, "combined_rating": 0, "ratings_used": []}

    sorted_ratings = sorted([max(0, min(100, r)) for r in ratings], reverse=True)

    remaining = 1.0
    for r in sorted_ratings:
        remaining *= (1.0 - r / 100.0)

    raw_decimal = 1.0 - remaining
    raw_percent = raw_decimal * 100.0

    # VA rounding: nearest 10, with 5 rounding up
    remainder = raw_percent % 10
    if remainder < 5:
        combined = int(raw_percent - remainder)
    else:
        combined = int(raw_percent - remainder + 10)

    combined = min(combined, 100)

    return {
        "raw_decimal": round(raw_decimal, 4),
        "raw_percent": round(raw_percent, 2),
        "combined_rating": combined,
        "ratings_used": sorted_ratings,
    }


def check_combined_rating_error(
    assigned_combined: int,
    individual_ratings: list[int],
    tolerance: int = 10,
) -> dict:
    """
    Check whether the VA's stated combined rating is mathematically correct.

    Args:
        assigned_combined: The combined rating stated in the decision letter.
        individual_ratings: List of individual condition ratings.
        tolerance: Allowable difference before flagging as error (default 10%).

    Returns:
        dict with keys: is_error, assigned, calculated, difference, explanation
    """
    result = calculate_combined_rating(individual_ratings)
    calculated = result["combined_rating"]
    difference = abs(assigned_combined - calculated)
    is_error = difference > tolerance

    explanation = (
        f"Assigned combined rating: {assigned_combined}%. "
        f"Calculated using VA whole-person math: {calculated}% "
        f"(raw: {result['raw_percent']:.1f}%). "
    )
    if is_error:
        explanation += (
            f"DISCREPANCY of {difference}% detected. "
            f"VA may have used simple addition instead of whole-person math, "
            f"or may have omitted a condition. Cite 38 CFR Part 4 Combined Ratings Table."
        )
    else:
        explanation += "Combined rating appears mathematically correct."

    return {
        "is_error": is_error,
        "assigned": assigned_combined,
        "calculated": calculated,
        "raw_percent": result["raw_percent"],
        "difference": difference,
        "ratings_used": result["ratings_used"],
        "explanation": explanation,
        "cfr_citation": "38 CFR Part 4, Combined Ratings Table",
    }
