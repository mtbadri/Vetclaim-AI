"""TDIU (Total Disability Individual Unemployability) eligibility checker.

38 CFR §4.16 - Individual Unemployability
"""

from __future__ import annotations

from tools.combined_rating import calculate_combined_rating


def tdiu_check(ratings: list[int], veteran_employed: bool = False) -> dict:
    """
    Check whether a veteran qualifies for TDIU under 38 CFR §4.16.

    TDIU pays at the 100% rate even if combined rating is below 100%.

    Eligibility criteria (§4.16(a) - schedular):
      - Single condition rated 60%+ OR
      - Multiple conditions with combined 70%+ AND at least one condition at 40%+

    Eligibility criteria (§4.16(b) - extraschedular):
      - Veteran is unable to maintain substantially gainful employment
        even if schedular thresholds are not met.

    Args:
        ratings: List of individual disability ratings.
        veteran_employed: Whether veteran is currently employed full-time.

    Returns:
        dict with TDIU eligibility verdict, basis, and relevant CFR citations.
    """
    combined_result = calculate_combined_rating(ratings)
    combined = combined_result["combined_rating"]
    sorted_ratings = combined_result["ratings_used"]

    max_single = max(ratings) if ratings else 0
    schedular_eligible = False
    basis = []

    # §4.16(a) single-condition threshold
    if max_single >= 60:
        schedular_eligible = True
        basis.append(
            f"Single condition rated {max_single}% meets the 60% threshold "
            f"for TDIU under 38 CFR §4.16(a)."
        )

    # §4.16(a) multi-condition threshold
    if combined >= 70 and max_single >= 40:
        schedular_eligible = True
        basis.append(
            f"Combined rating {combined}% (≥70%) with highest single rating "
            f"{max_single}% (≥40%) meets multi-condition threshold "
            f"for TDIU under 38 CFR §4.16(a)."
        )

    # §4.16(b) extraschedular
    extraschedular_note = None
    if not schedular_eligible:
        extraschedular_note = (
            f"Schedular thresholds not met (combined: {combined}%, highest single: {max_single}%). "
            f"However, if service-connected disabilities prevent substantially gainful employment, "
            f"TDIU may still be awarded on an extraschedular basis under 38 CFR §4.16(b). "
            f"This requires referral to VA Director of Compensation."
        )

    monthly_pay_100 = 3927.08  # 2026 rate for veteran alone at 100%

    result = {
        "tdiu_schedular_eligible": schedular_eligible,
        "basis": basis,
        "individual_ratings": sorted_ratings,
        "combined_rating": combined,
        "highest_single_rating": max_single,
        "veteran_employed": veteran_employed,
        "extraschedular_note": extraschedular_note,
        "cfr_citation": "38 CFR §4.16 - Individual Unemployability",
        "potential_monthly_pay_usd": monthly_pay_100,
        "potential_annual_pay_usd": monthly_pay_100 * 12,
    }

    if schedular_eligible and not veteran_employed:
        result["recommendation"] = (
            "Veteran appears TDIU-eligible. File VA Form 21-8940 "
            "(Veteran's Application for Increased Compensation Based on Unemployability). "
            f"If approved, veteran receives 100% pay (${monthly_pay_100:,.2f}/month) "
            f"regardless of combined rating ({combined}%). "
            f"Cite: 38 CFR §4.16(a)."
        )
    elif schedular_eligible and veteran_employed:
        result["recommendation"] = (
            "Veteran meets rating thresholds for TDIU but is currently employed. "
            "TDIU requires veteran to be unable to maintain substantially gainful employment. "
            "Marginal employment (income below poverty threshold) still qualifies."
        )
    elif extraschedular_note:
        result["recommendation"] = extraschedular_note

    return result
