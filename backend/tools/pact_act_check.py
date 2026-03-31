"""PACT Act presumptive condition checker."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "pact_act_conditions.json"
_pact_data: dict | None = None

# Service era keyword mapping for flexible input matching
_ERA_KEYWORDS = {
    "burn_pit": [
        "iraq", "afghanistan", "syria", "post-9/11", "post 9/11", "gwot",
        "oif", "oef", "ond", "southwest asia", "djibouti", "kuwait",
        "qatar", "saudi", "bahrain", "oman", "uae", "somalia", "jordan",
        "al udeid", "camp arifjan", "camp buehring", "bagram", "kandahar",
        "fallujah", "mosul", "ramadi", "tikrit",
    ],
    "agent_orange": [
        "vietnam", "viet nam", "korea", "korean dmz", "thailand", "laos",
        "cambodia", "johnston atoll", "guam", "american samoa",
    ],
    "camp_lejeune": [
        "camp lejeune", "lejeune", "mcas new river", "new river",
    ],
    "radiation": [
        "hiroshima", "nagasaki", "nuclear test", "atmospheric test",
        "enewetak", "palomares", "thule", "amchitka",
    ],
}


def _load() -> dict:
    global _pact_data
    if _pact_data is None:
        with open(_DATA_PATH) as f:
            _pact_data = json.load(f)
    return _pact_data


def _detect_eras(deployment_locations: list[str], service_era: str | None) -> list[str]:
    """Determine which PACT Act exposure categories apply based on locations/era."""
    combined = " ".join(deployment_locations + ([service_era] if service_era else [])).lower()
    matched = []
    for era, keywords in _ERA_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            matched.append(era)
    return matched


def pact_act_check(
    condition_name: str,
    deployment_locations: list[str],
    service_era: str | None = None,
) -> dict:
    """
    Check whether a condition qualifies as a PACT Act presumptive.

    Args:
        condition_name: Name of the condition (e.g. 'asthma', 'diabetes', 'PTSD').
        deployment_locations: List of deployment locations from service records.
        service_era: Optional service era string (e.g. 'post-9/11', 'Vietnam').

    Returns:
        dict with eligibility verdict, applicable exposure categories, and legal citation.
    """
    data = _load()
    categories = data.get("exposure_categories", {})
    matched_eras = _detect_eras(deployment_locations, service_era)
    condition_lower = condition_name.lower()

    matches = []
    for era in matched_eras:
        cat = categories.get(era, {})
        for entry in cat.get("presumptive_conditions", []):
            entry_condition = entry.get("condition", "").lower()
            # Fuzzy match: check if condition words overlap
            condition_words = set(condition_lower.split())
            entry_words = set(entry_condition.split())
            if condition_words & entry_words or condition_lower in entry_condition or entry_condition in condition_lower:
                matches.append({
                    "exposure_category": era,
                    "exposure_label": cat.get("label", era),
                    "matched_condition": entry.get("condition"),
                    "icd_codes": entry.get("icd_codes", []),
                    "notes": entry.get("notes", ""),
                    "qualifying_locations": cat.get("qualifying_locations", []),
                    "qualifying_dates": cat.get("qualifying_dates", {}),
                })

    eligible = len(matches) > 0

    result = {
        "condition": condition_name,
        "pact_act_eligible": eligible,
        "deployment_locations_checked": deployment_locations,
        "service_era": service_era,
        "matched_exposure_eras": matched_eras,
        "matches": matches,
        "legal_citation": "Sergeant First Class Heath Robinson PACT Act of 2022, P.L. 117-168; 38 CFR §3.309",
    }

    if eligible:
        result["explanation"] = (
            f"'{condition_name}' appears to qualify as a PACT Act presumptive condition "
            f"based on service in: {', '.join(deployment_locations)}. "
            f"No nexus letter required - eligibility is presumed by law. "
            f"Cite: {result['legal_citation']}."
        )
    else:
        result["explanation"] = (
            f"No direct PACT Act presumptive match found for '{condition_name}' "
            f"with the provided locations. A nexus letter from a physician may still "
            f"establish service connection. Matched exposure eras: {matched_eras or 'none detected'}."
        )

    return result


def list_burn_pit_conditions() -> list[str]:
    """Return all burn pit presumptive condition names."""
    data = _load()
    return [
        c["condition"]
        for c in data["exposure_categories"]["burn_pit"]["presumptive_conditions"]
    ]


def list_agent_orange_conditions() -> list[str]:
    """Return all Agent Orange presumptive condition names."""
    data = _load()
    return [
        c["condition"]
        for c in data["exposure_categories"]["agent_orange"]["presumptive_conditions"]
    ]
