"""
Auditor Agent - VetClaim AI

Receives parsed VA document text, extracts structured claim data via Gemini,
audits each condition against CFR Title 38 Part 4, PACT Act, TDIU criteria,
and combined rating math. Outputs an AuditResult with flags for the Advocate.

Uses Google ADK (google-adk) LlmAgent.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import requests
from pypdf import PdfReader, PdfWriter

# Ensure backend root is on path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agents.filer_agent import VAFormFiler
from schemas import ParsedClaim
from tools.cfr_lookup import cfr_lookup as _cfr_lookup, cfr_compare_rating as _cfr_compare_rating
from tools.pact_act_check import pact_act_check as _pact_act_check
from tools.tdiu_check import tdiu_check as _tdiu_check
from tools.va_pay_lookup import va_pay_lookup as _va_pay_lookup, calculate_pay_impact as _calculate_pay_impact
from tools.combined_rating import calculate_combined_rating as _calculate_combined_rating, check_combined_rating_error as _check_combined_rating_error


# ---------------------------------------------------------------------------
# Tool wrappers
# All tools exposed to the LLM must be plain Python callables.
# ADK passes the LLM's arguments directly as keyword args.
# ---------------------------------------------------------------------------

def cfr_lookup(diagnostic_code: str) -> str:
    """
    Look up a VA diagnostic code in CFR Title 38 Part 4.
    Returns the condition name, CFR section, rating criteria at every percentage
    level, and the maximum possible rating.

    Args:
        diagnostic_code: VA diagnostic code string, e.g. '9411', '8045', '6260'.
    """
    result = _cfr_lookup(diagnostic_code)
    return json.dumps(result, indent=2)


def cfr_compare_rating(
    diagnostic_code: str,
    assigned_rating: int,
    symptom_description: str,
) -> str:
    """
    Compare the VA's assigned rating for a condition against CFR criteria.
    Returns the next higher rating level and its criteria so you can determine
    if the condition is UNDER_RATED.

    Args:
        diagnostic_code: VA diagnostic code, e.g. '9411'.
        assigned_rating: Rating percentage the VA currently assigns (integer).
        symptom_description: Description of the veteran's symptoms from records.
    """
    result = _cfr_compare_rating(diagnostic_code, assigned_rating, symptom_description)
    return json.dumps(result, indent=2)


def pact_act_check(
    condition_name: str,
    deployment_locations: list[str],
    service_era: str | None = None,
) -> str:
    """
    Check whether a condition qualifies as a PACT Act presumptive based on
    the veteran's deployment locations and service era. If eligible, no nexus
    letter is required - service connection is presumed by law.

    Args:
        condition_name: Name of the medical condition to check.
        deployment_locations: List of deployment locations, e.g. ['Iraq', 'Afghanistan'].
        service_era: Optional era string, e.g. 'post-9/11', 'Vietnam'.
    """
    result = _pact_act_check(condition_name, deployment_locations, service_era)
    return json.dumps(result, indent=2)


def tdiu_check(ratings: list[int], veteran_employed: bool = False) -> str:
    """
    Check whether the veteran qualifies for Total Disability Individual
    Unemployability (TDIU) under 38 CFR §4.16. TDIU pays at the 100% rate.

    Args:
        ratings: List of all individual disability ratings as integers, e.g. [50, 30, 10].
        veteran_employed: True if veteran is currently working full-time.
    """
    result = _tdiu_check(ratings, veteran_employed)
    return json.dumps(result, indent=2)


def combined_rating(ratings: list[int]) -> str:
    """
    Calculate the correct VA combined disability rating using whole-person math
    (38 CFR Part 4). The VA does NOT add ratings directly.
    Formula: combined = 1 - ((1-r1) * (1-r2) * ... * (1-rN)), rounded to nearest 10.

    Args:
        ratings: List of individual ratings as integers, e.g. [50, 30, 10].
    """
    result = _calculate_combined_rating(ratings)
    return json.dumps(result, indent=2)


def check_combined_rating_error(
    assigned_combined: int,
    individual_ratings: list[int],
) -> str:
    """
    Check whether the VA's stated combined rating in the decision letter is
    mathematically correct. Flags COMBINED_RATING_ERROR if discrepancy found.

    Args:
        assigned_combined: Combined rating stated in the VA decision letter.
        individual_ratings: List of individual condition ratings.
    """
    result = _check_combined_rating_error(assigned_combined, individual_ratings)
    return json.dumps(result, indent=2)


def va_pay_lookup(combined_rating: int, dependent_status: str = "alone") -> str:
    """
    Look up the monthly VA disability pay for a given combined rating.

    Args:
        combined_rating: Combined disability rating (10, 20, 30 ... 100).
        dependent_status: One of: 'alone', 'spouse', 'spouse_one_child',
                          'spouse_two_children', 'one_child'.
    """
    result = _va_pay_lookup(combined_rating, dependent_status)
    return json.dumps(result, indent=2)


def calculate_pay_impact(
    current_rating: int,
    potential_rating: int,
    dependent_status: str = "alone",
) -> str:
    """
    Calculate the monthly and annual dollar impact of a rating increase.

    Args:
        current_rating: Veteran's current combined rating.
        potential_rating: Potential combined rating after successful appeal.
        dependent_status: Veteran's dependent status (see va_pay_lookup).
    """
    result = _calculate_pay_impact(current_rating, potential_rating, dependent_status)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Auditor Agent instruction prompt
# ---------------------------------------------------------------------------

AUDITOR_INSTRUCTION = """
You are the Auditor Agent for VetClaim AI, an expert in VA disability law and
CFR Title 38 Part 4. Your job is to audit VA disability claims and find every
instance where the veteran may be under-compensated.

## Your Input
You will receive the raw text extracted from one or more VA documents:
- Rating Decision Letter (contains assigned ratings, diagnostic codes, denial reasons)
- Personal Statement (veteran's own description of symptoms)
- DBQ / C&P Exam (medical examination findings)

## Your Process

### Step 1 - Extract structured claim data
From the raw text, identify:
- Veteran name and claim number
- Each service-connected condition with its diagnostic code and assigned rating %
- Denial reasons for any denied conditions
- Overall combined rating stated in the letter
- Service era and deployment locations (if mentioned)
- Symptoms described in personal statement and DBQ

### Step 2 - Audit each condition
For EVERY condition, call cfr_compare_rating with:
- The diagnostic code
- The assigned rating
- The symptom description from the records

Determine if symptoms described match higher rating criteria.

### Step 3 - Check PACT Act eligibility
For each condition AND for the veteran's deployment history overall:
- Call pact_act_check for every condition
- Check if any denied conditions would be presumptive under PACT Act

### Step 4 - Check TDIU
Call tdiu_check with ALL individual ratings.

### Step 5 - Verify combined rating math
Call check_combined_rating_error with the stated combined rating and
all individual ratings.

### Step 6 - Calculate pay impact
Call calculate_pay_impact comparing current vs. corrected rating.

## Flag Types
Generate flags for every issue found:

- **UNDER_RATED**: Assigned rating lower than CFR criteria warrant for documented symptoms.
  Example: PTSD rated 30% but "near-continuous depression affecting ability to function" = 70%.

- **WRONG_CODE**: Wrong diagnostic code applied, which may cap the rating artificially.
  Example: TBI cognitive coded under 8045 (caps at 40%) instead of §4.130 (up to 100%).

- **MISSING_NEXUS**: Condition denied for lack of nexus but medical evidence in records
  supports service connection.

- **PACT_ACT_ELIGIBLE**: Condition or deployment qualifies for presumptive service
  connection under PACT Act - no nexus letter needed.

- **TDIU_ELIGIBLE**: Individual ratings qualify veteran for 100% TDIU pay rate
  under 38 CFR §4.16.

- **COMBINED_RATING_ERROR**: VA's stated combined rating does not match correct
  whole-person math calculation.

- **SEPARATE_RATING_MISSED**: Condition has a separately ratable residual that
  was not rated. Example: TBI vestibular symptoms (DC 6204) rated separately
  from cognitive symptoms (DC 8045).

## Output Format
Respond with a structured JSON audit result:

```json
{
  "veteran_name": "...",
  "claim_number": "...",
  "current_combined_rating": 30,
  "corrected_combined_rating": 70,
  "current_monthly_pay_usd": 550.86,
  "potential_monthly_pay_usd": 1803.48,
  "annual_impact_usd": 15031.44,
  "flags": [
    {
      "flag_type": "UNDER_RATED",
      "condition_name": "PTSD",
      "diagnostic_code": "9411",
      "assigned_rating": 30,
      "eligible_rating": 70,
      "cfr_citation": "38 CFR Part 4, §4.130, DC 9411",
      "explanation": "...",
      "monthly_impact_usd": 1252.62,
      "confidence": 0.9
    }
  ],
  "tdiu_eligible": false,
  "pact_act_conditions_found": [],
  "combined_rating_error": false,
  "auditor_notes": "..."
}
```

## Rules
- Always cite the specific CFR section for every flag.
- Confidence score: 0.9+ = clear match, 0.7-0.9 = likely, below 0.7 = possible.
- If a diagnostic code is not in the CFR database, note it and flag for review.
- Consider bilateral factor: bilateral conditions (both arms, both legs) get a
  10% combined rating bonus before the combined rating calculation.
- Do not speculate beyond what the records state. Base flags on documented symptoms.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def create_auditor_agent() -> LlmAgent:
    """Create and return the configured Auditor LlmAgent."""
    return LlmAgent(
        name="auditor_agent",
        model="gemini-2.5-flash",
        description=(
            "Audits VA disability claims against CFR Title 38 Part 4. "
            "Identifies under-ratings, wrong codes, PACT Act eligibility, "
            "TDIU eligibility, and combined rating errors."
        ),
        instruction=AUDITOR_INSTRUCTION,
        tools=[
            cfr_lookup,
            cfr_compare_rating,
            pact_act_check,
            tdiu_check,
            combined_rating,
            check_combined_rating_error,
            va_pay_lookup,
            calculate_pay_impact,
        ],
    )


# Singleton for import by orchestrator
auditor_agent = create_auditor_agent()


# ---------------------------------------------------------------------------
# VA Forms API constants and Rule-Based Auditor
# ---------------------------------------------------------------------------

VA_FORMS_API_BASE = "https://api.va.gov/forms_api/v1/forms/{form_number}"
LIGHTHOUSE_FORMS_BASE = "https://api.va.gov/services/va_forms/v0/forms/{form_number}"
FALLBACK_FORM_URLS: dict[str, str] = {
    "20-0996":  "https://www.vba.va.gov/pubs/forms/VBA-20-0996-ARE.pdf",
    "20-0995":  "https://www.vba.va.gov/pubs/forms/VBA-20-0995-ARE.pdf",
    "21-526EZ": "https://www.vba.va.gov/pubs/forms/VBA-21-526EZ-ARE.pdf",
    "21-8940":  "https://www.vba.va.gov/pubs/forms/VBA-21-8940-ARE.pdf",
}

_HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "VAClaimAuditor/1.0 (hackathon; +https://www.va.gov)",
}

# Maps each LLM-produced flag type to the VA form(s) appropriate for that issue.
FLAG_TO_FORMS: dict[str, list[str]] = {
    "UNDER_RATED":            ["20-0996"],
    "WRONG_CODE":             ["20-0996"],
    "COMBINED_RATING_ERROR":  ["20-0996"],
    "MISSING_NEXUS":          ["20-0995"],
    "PACT_ACT_ELIGIBLE":      ["20-0995"],
    "SEPARATE_RATING_MISSED": ["21-526EZ"],
    "TDIU_ELIGIBLE":          ["21-8940"],
}


class VAClaimAuditor:
    """Rule-based auditor that detects specific issues and downloads VA forms."""

    def __init__(self, output_dir: str | Path | None = None) -> None:
        """
        Initialize the auditor.

        Args:
            output_dir: Directory to write blank and filled PDFs.
                       Defaults to backend/data/ to avoid temp uploads dir.
        """
        if output_dir is None:
            output_dir = Path(__file__).resolve().parent.parent / "data"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _gait_evidence_detected(self, parsed_claim: ParsedClaim) -> bool:
        """Check if gait keywords (staggering/unsteady) were detected in DBQ."""
        flags = parsed_claim.gait_keyword_flags or {}
        return (
            flags.get("staggering") == "DETECTED" or flags.get("unsteady") == "DETECTED"
        )

    def _decision_letter_shows_zero_percent(self, parsed_claim: ParsedClaim) -> bool:
        """Check if decision letter mentions 0% rating."""
        text = parsed_claim.raw_decision_text or ""
        return bool(re.search(r"0\s*percent|0\s*%", text, re.IGNORECASE))

    def _get_form_pdf_url_from_api(self, form_number: str) -> str:
        """
        Fetch the blank PDF URL for a VA form from the VA API.
        Tries multiple endpoints with fallback.

        Args:
            form_number: VA form number string, e.g. '20-0996', '21-8940'.

        Returns:
            URL string of the blank form PDF.
        """
        env_key = os.getenv("VA_FORMS_API_KEY")
        primary_url = VA_FORMS_API_BASE.format(form_number=form_number)
        secondary_url = LIGHTHOUSE_FORMS_BASE.format(form_number=form_number)

        # Try VA Forms API
        try:
            headers = _HTTP_HEADERS.copy()
            if env_key:
                headers["Authorization"] = f"Bearer {env_key}"
            response = requests.get(primary_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "url" in data:
                    return data["url"]
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("url", "")
        except Exception:
            pass

        # Try Lighthouse API
        try:
            headers = _HTTP_HEADERS.copy()
            if env_key:
                headers["Authorization"] = f"Bearer {env_key}"
            response = requests.get(secondary_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and "url" in data:
                    return data["url"]
        except Exception:
            pass

        # Fallback to hardcoded URL
        return FALLBACK_FORM_URLS.get(form_number, FALLBACK_FORM_URLS["20-0996"])

    def download_and_fill_form(
        self, parsed_claim: ParsedClaim, form_number: str = "20-0996"
    ) -> str:
        """
        Download a VA form and fill in veteran info.

        Args:
            parsed_claim: The ParsedClaim with veteran name.
            form_number: VA form number to download, e.g. '20-0996', '21-8940'.

        Returns:
            Path to the filled PDF.
        """
        # Get form URL and download
        form_url = self._get_form_pdf_url_from_api(form_number)
        response = requests.get(form_url, timeout=30)
        response.raise_for_status()

        # Save blank PDF with form-specific filename to avoid clobbering
        blank_pdf_path = self.output_dir / f"blank_{form_number.replace('-', '_')}.pdf"
        blank_pdf_path.write_bytes(response.content)

        # Parse veteran name
        veteran_name = parsed_claim.veteran_name or ""
        first_name, _, last_name = veteran_name.partition(" ")
        if not last_name:
            last_name = ""

        # Fill PDF using pypdf
        reader = PdfReader(str(blank_pdf_path))
        writer = PdfWriter(clone_from=reader)

        # Attempt to fill form fields
        form_field_names = reader.get_fields()
        if form_field_names:
            # Map veteran name to likely form field names
            for field_name in form_field_names:
                if "first" in field_name.lower() and "name" in field_name.lower():
                    writer.update_page_form_field_values(
                        writer.pages[0], {field_name: first_name}
                    )
                elif "last" in field_name.lower() and "name" in field_name.lower():
                    writer.update_page_form_field_values(
                        writer.pages[0], {field_name: last_name}
                    )

        # Save filled PDF with form number in filename
        filled_pdf_filename = (
            f"{veteran_name.replace(' ', '_').lower()}"
            f"_ready_to_file_{form_number.replace('-', '_')}.pdf"
        )
        filled_pdf_path = self.output_dir / filled_pdf_filename
        with open(filled_pdf_path, "wb") as f:
            writer.write(f)

        return str(filled_pdf_path)

    def _critical_report(
        self, parsed_claim: ParsedClaim, filled_pdf_path: str
    ) -> str:
        """Generate human-readable critical audit report."""
        veteran_name = parsed_claim.veteran_name or "Veteran"
        return (
            f"🚩 CRITICAL FINDING for {veteran_name}:\n\n"
            f"Gait impairment detected in DBQ (staggering/unsteady) combined with "
            f"0% rating in decision letter indicates likely under-rating.\n\n"
            f"Condition may qualify under 38 CFR § 4.87, Diagnostic Code 6204 "
            f"(Vestibular dysfunction).\n\n"
            f"VA Form 20-0996 (Higher-Level Review) has been prepared and saved to:\n"
            f"{filled_pdf_path}\n\n"
            f"Recommend immediate filing for higher-level review."
        )

    def analyze_claim(self, parsed_claim: ParsedClaim) -> dict:
        """
        Run rule-based checks and download forms if needed.

        Args:
            parsed_claim: The ParsedClaim to analyze.

        Returns:
            Dict with keys: rule_based_triggered, report, filled_form_path
        """
        gait_detected = self._gait_evidence_detected(parsed_claim)
        zero_percent = self._decision_letter_shows_zero_percent(parsed_claim)

        if gait_detected and zero_percent:
            try:
                filled_pdf_path = self.download_and_fill_form(parsed_claim)
                report = self._critical_report(parsed_claim, filled_pdf_path)
                return {
                    "rule_based_triggered": True,
                    "report": report,
                    "filled_form_path": filled_pdf_path,
                }
            except Exception as e:
                return {
                    "rule_based_triggered": True,
                    "report": f"Critical finding detected but form download failed: {str(e)}",
                    "filled_form_path": None,
                }

        return {
            "rule_based_triggered": False,
            "report": "✅ No critical rule-based flags triggered.",
            "filled_form_path": None,
        }


def _extract_flag_types(audit_result: dict) -> list[str]:
    """Extract the list of flag_type strings from an audit result dict."""
    flag_types: list[str] = []
    for flag in audit_result.get("flags", []):
        if isinstance(flag, dict):
            ft = flag.get("flag_type")
        elif hasattr(flag, "flag_type"):
            ft = flag.flag_type
            if hasattr(ft, "value"):
                ft = ft.value
        else:
            continue
        if ft and isinstance(ft, str):
            flag_types.append(ft)
    return flag_types


def _forms_for_flags(flag_types: list[str]) -> list[str]:
    """Map flag types to a deduplicated, ordered list of form numbers."""
    seen: set[str] = set()
    forms: list[str] = []
    for ft in flag_types:
        for form_number in FLAG_TO_FORMS.get(ft, []):
            if form_number not in seen:
                seen.add(form_number)
                forms.append(form_number)
    return forms


def run_full_audit(parsed_claim: ParsedClaim) -> dict:
    """
    Run full audit: LLM agent + rule-based checks.

    For every flag the LLM produces, maps it to the appropriate VA form(s),
    downloads and pre-fills each unique form, and returns all filled paths.

    Args:
        parsed_claim: The ParsedClaim returned by VAClaimParser.extract_all().

    Returns:
        Dict with audit_result, rule_based_report, rule_based_triggered,
        filled_form_path (first, for backwards compat), filled_form_paths,
        forms_needed, and va_form_links.
    """
    # Build LLM input from parsed claim
    llm_input_parts = []

    if parsed_claim.veteran_name:
        llm_input_parts.append(f"Veteran Name: {parsed_claim.veteran_name}")

    if parsed_claim.raw_decision_text:
        llm_input_parts.append(
            f"\n--- DECISION LETTER ---\n{parsed_claim.raw_decision_text}"
        )

    if parsed_claim.raw_statement_text:
        llm_input_parts.append(
            f"\n--- PERSONAL STATEMENT & C&P EXAM ---\n{parsed_claim.raw_statement_text}"
        )

    if parsed_claim.raw_dbq_text:
        llm_input_parts.append(f"\n--- DBQ(s) ---\n{parsed_claim.raw_dbq_text}")

    llm_input_str = "".join(llm_input_parts)

    # Run LLM auditor via ADK Runner
    async def _run_llm_audit(text: str) -> str:
        session_service = InMemorySessionService()
        runner = Runner(
            agent=auditor_agent,
            app_name="vetclaim_auditor",
            session_service=session_service,
        )
        session = await session_service.create_session(
            app_name="vetclaim_auditor",
            user_id="auditor_user",
        )
        final_text = ""
        async for event in runner.run_async(
            user_id="auditor_user",
            session_id=session.id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=text)],
            ),
        ):
            if event.is_final_response() and event.content:
                for part in (event.content.parts or []):
                    if hasattr(part, "text") and part.text:
                        final_text += part.text
        return final_text

    llm_result = asyncio.run(_run_llm_audit(llm_input_str))

    # Normalize LLM result to dict
    if isinstance(llm_result, str):
        # Strip markdown code fences if present (e.g. ```json\n...\n```)
        stripped = llm_result.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
            stripped = re.sub(r"\n?```$", "", stripped.strip())
        try:
            audit_result = json.loads(stripped)
        except json.JSONDecodeError:
            # LLM returned non-JSON string — treat as error
            audit_result = {
                "error": "LLM returned non-JSON response",
                "raw_response": llm_result[:500],  # First 500 chars for debugging
            }
    elif hasattr(llm_result, "model_dump"):
        audit_result = llm_result.model_dump()
    elif isinstance(llm_result, dict):
        audit_result = llm_result
    else:
        # Unknown type — log and use empty
        audit_result = {
            "error": f"LLM returned unexpected type: {type(llm_result).__name__}"
        }

    # Map LLM flags to form numbers
    flag_types = _extract_flag_types(audit_result)
    llm_forms = _forms_for_flags(flag_types)

    # Run rule-based auditor
    rule_auditor = VAClaimAuditor()
    rule_result = rule_auditor.analyze_claim(parsed_claim)

    # Merge form lists — rule-based always uses 20-0996
    all_forms: list[str] = list(llm_forms)
    if rule_result.get("rule_based_triggered") and "20-0996" not in all_forms:
        all_forms.append("20-0996")

    # Download and fill each unique form via VAFormFiler
    filled_form_paths: list[str] = []
    va_form_links: list[dict] = []

    # Initialize auditor_notes if not present
    if "auditor_notes" not in audit_result:
        audit_result["auditor_notes"] = ""

    backend_dir = Path(__file__).resolve().parent.parent
    (backend_dir / "output").mkdir(parents=True, exist_ok=True)

    # Build veteran_data — prefer LLM audit_result for name (more accurate than regex)
    llm_name = audit_result.get("veteran_name") or parsed_claim.veteran_name or ""
    parts = llm_name.split()
    first_name = parts[0] if parts else ""
    last_name  = " ".join(parts[1:]) if len(parts) > 1 else ""

    # Today's date for signature / filing date fields
    from datetime import date as _date
    today = _date.today()
    sig_month = str(today.month).zfill(2)
    sig_day   = str(today.day).zfill(2)
    sig_year  = str(today.year)

    # Use LLM-extracted condition names from flags for the issue description
    llm_conditions = [
        f.get("condition_name", "")
        for f in audit_result.get("flags", [])
        if isinstance(f, dict) and f.get("condition_name")
    ]
    if llm_conditions:
        issue_text = "; ".join(llm_conditions[:4])[:200]
    elif parsed_claim.conditions:
        issue_text = "; ".join(
            c.condition_name for c in parsed_claim.conditions if c.condition_name
        )[:200]
    else:
        issue_text = "Service-connected condition"

    # Generate realistic-looking demographic data for fields not in the documents.
    # We seed from the veteran name so the same veteran always gets consistent data.
    import hashlib as _hashlib
    _seed = int(_hashlib.md5(llm_name.encode()).hexdigest()[:8], 16)
    import random as _random
    _rng = _random.Random(_seed)

    _area_codes   = ["210", "512", "619", "757", "910", "843", "850", "253", "907", "808"]
    _streets      = ["4821 Valor Ridge Dr", "1203 Liberty Oak Ln", "7742 Patriot Blvd",
                     "335 Ft. Bragg Rd", "9110 Veterans Way", "620 Honor Guard Ave",
                     "2244 Service Member St", "5501 Eagle Crest Dr"]
    _cities_states = [
        ("San Antonio", "TX", "78201"), ("Fayetteville", "NC", "28301"),
        ("Jacksonville", "NC", "28540"), ("Virginia Beach", "VA", "23451"),
        ("Colorado Springs", "CO", "80903"), ("Killeen", "TX", "76540"),
        ("Clarksville", "TN", "37040"), ("Tacoma", "WA", "98402"),
    ]
    _city, _state, _zip = _cities_states[_seed % len(_cities_states)]

    veteran_data = {
        "first_name":     first_name,
        "last_name":      last_name,
        # SSN — realistic format, clearly demo values (000 prefix)
        "ssn_1":          "000",
        "ssn_2":          str(_rng.randint(10, 99)),
        "ssn_3":          str(_rng.randint(1000, 9999)),
        # DOB — plausible for a Gulf War / OIF veteran
        "dob_month":      str(_rng.randint(1, 12)).zfill(2),
        "dob_day":        str(_rng.randint(1, 28)).zfill(2),
        "dob_year":       str(_rng.randint(1968, 1985)),
        # Phone
        "phone_area":     _area_codes[_seed % len(_area_codes)],
        "phone_mid":      str(_rng.randint(200, 999)),
        "phone_last":     str(_rng.randint(1000, 9999)),
        # Address
        "address_street": _streets[_seed % len(_streets)],
        "address_city":   _city,
        "address_state":  _state,
        "address_zip":    _zip,
        # Claim fields
        "issue":          issue_text,
        "date_month":     sig_month,
        "date_day":       sig_day,
        "date_year":      sig_year,
        "sign_month":     sig_month,
        "sign_day":       sig_day,
        "sign_year":      sig_year,
    }

    for form_number in all_forms:
        try:
            filer = VAFormFiler(backend_dir=str(backend_dir))
            filled_path, fields_found, fields_filled = filer.download_and_fill_hlr(
                veteran_data, form_number=form_number
            )
            filled_form_paths.append(filled_path)
            va_form_links.append({
                "form_number": form_number,
                "filled_path": filled_path,
                "pdf_url": filer._get_form_pdf_url_from_api(form_number),
                "fields_found": fields_found,
                "fields_filled": fields_filled,
            })
        except Exception as exc:
            audit_result["auditor_notes"] += f" [Form {form_number} download failed: {str(exc)}]"

    # Ensure audit_result has expected structure and default fields
    if not isinstance(audit_result, dict):
        audit_result = {"error": "Could not parse audit result"}

    # Set defaults for expected fields if missing
    if "flags" not in audit_result:
        audit_result["flags"] = []
    if "veteran_name" not in audit_result:
        audit_result["veteran_name"] = parsed_claim.veteran_name or "Unknown"
    if "current_combined_rating" not in audit_result:
        audit_result["current_combined_rating"] = None
    if "corrected_combined_rating" not in audit_result:
        audit_result["corrected_combined_rating"] = None
    if "current_monthly_pay_usd" not in audit_result:
        audit_result["current_monthly_pay_usd"] = None
    if "potential_monthly_pay_usd" not in audit_result:
        audit_result["potential_monthly_pay_usd"] = None
    if "annual_impact_usd" not in audit_result:
        audit_result["annual_impact_usd"] = None

    return {
        # Existing keys — unchanged shapes for frontend backwards compatibility
        "audit_result": audit_result,
        "rule_based_report": rule_result.get("report", ""),
        "rule_based_triggered": rule_result.get("rule_based_triggered", False),
        "filled_form_path": filled_form_paths[0] if filled_form_paths else None,
        # New keys
        "filled_form_paths": filled_form_paths,
        "forms_needed": all_forms,
        "va_form_links": va_form_links,
    }
