"""CFR Title 38 Part 4 lookup tool - maps diagnostic codes to rating criteria."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "cfr38_part4.json"
_cfr_data: dict | None = None


def _load() -> dict:
    global _cfr_data
    if _cfr_data is None:
        with open(_DATA_PATH) as f:
            _cfr_data = json.load(f)
    return _cfr_data


def cfr_lookup(diagnostic_code: str) -> dict:
    """
    Look up a VA diagnostic code in CFR Title 38 Part 4.

    Returns the condition name, CFR section, body system, rating criteria
    at each percentage level, and the maximum possible rating.

    Args:
        diagnostic_code: VA diagnostic code (e.g. '9411', '8045', '6260').

    Returns:
        dict with condition info and rating_criteria, or error if not found.
    """
    data = _load()
    code = str(diagnostic_code).strip()
    entry = data.get(code)
    if not entry:
        return {
            "found": False,
            "diagnostic_code": code,
            "error": (
                f"Diagnostic code {code} not found in CFR database. "
                "May be a rare condition or unlisted code. "
                "Check eCFR.gov/current/title-38/chapter-I/part-4 for full schedule."
            ),
        }
    return {
        "found": True,
        "diagnostic_code": code,
        **entry,
    }


def cfr_compare_rating(diagnostic_code: str, assigned_rating: int, symptom_description: str) -> dict:
    """
    Compare an assigned rating against CFR criteria and identify if it is under-rated.

    Args:
        diagnostic_code: VA diagnostic code.
        assigned_rating: Rating percentage currently assigned by VA.
        symptom_description: Free-text description of the veteran's symptoms from records.

    Returns:
        dict with rating comparison, next eligible rating, and CFR citation.
    """
    lookup = cfr_lookup(diagnostic_code)
    if not lookup.get("found"):
        return lookup

    criteria = lookup.get("rating_criteria", {})
    max_rating = lookup.get("max_rating", 100)
    condition = lookup.get("condition", "Unknown")
    cfr_section = lookup.get("cfr_section", "38 CFR Part 4")

    # Build ordered list of available rating levels
    available_levels = sorted([int(k) for k in criteria.keys()])
    next_level = None
    for level in available_levels:
        if level > assigned_rating:
            next_level = level
            break

    result = {
        "diagnostic_code": diagnostic_code,
        "condition": condition,
        "cfr_section": cfr_section,
        "assigned_rating": assigned_rating,
        "max_rating": max_rating,
        "available_rating_levels": available_levels,
        "next_rating_level": next_level,
        "all_criteria": criteria,
        "assigned_rating_criteria": criteria.get(str(assigned_rating), "No criteria found for this rating level"),
        "next_level_criteria": criteria.get(str(next_level)) if next_level else None,
        "notes": lookup.get("notes", ""),
        "symptom_description_provided": symptom_description,
        "instruction": (
            f"Compare the symptom description against the rating criteria above. "
            f"If symptoms match criteria at {next_level}% or higher, flag as UNDER_RATED. "
            f"Cite {cfr_section} in the appeal letter."
        ),
    }
    return result


def get_all_codes() -> list[str]:
    """Return all diagnostic codes in the CFR database."""
    return list(_load().keys())
