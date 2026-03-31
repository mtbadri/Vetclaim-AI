"""Pydantic schemas shared across all agents."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Parser output (produced by va_claim_parser.py / parser agent)
# ---------------------------------------------------------------------------

class ParsedCondition(BaseModel):
    condition_name: str
    diagnostic_code: str | None = None
    assigned_rating: int | None = None
    denial_reason: str | None = None
    body_system: str | None = None
    raw_text_excerpt: str | None = None


class ParsedClaim(BaseModel):
    """Structured data extracted from VA documents by the parser agent."""
    veteran_name: str | None = None
    claim_number: str | None = None
    decision_date: str | None = None
    service_era: str | None = None
    deployment_locations: list[str] = Field(default_factory=list)
    mos: str | None = None
    conditions: list[ParsedCondition] = Field(default_factory=list)
    overall_combined_rating: int | None = None
    raw_decision_text: str | None = None
    raw_statement_text: str | None = None
    raw_dbq_text: str | None = None
    gait_keyword_flags: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Auditor output
# ---------------------------------------------------------------------------

class FlagType(str, Enum):
    UNDER_RATED = "UNDER_RATED"
    WRONG_CODE = "WRONG_CODE"
    MISSING_NEXUS = "MISSING_NEXUS"
    PACT_ACT_ELIGIBLE = "PACT_ACT_ELIGIBLE"
    TDIU_ELIGIBLE = "TDIU_ELIGIBLE"
    COMBINED_RATING_ERROR = "COMBINED_RATING_ERROR"
    SEPARATE_RATING_MISSED = "SEPARATE_RATING_MISSED"


class AuditFlag(BaseModel):
    flag_type: FlagType
    condition_name: str
    diagnostic_code: str | None = None
    assigned_rating: int | None = None
    eligible_rating: int | None = None
    cfr_citation: str | None = None
    explanation: str
    monthly_impact_usd: float | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class AuditResult(BaseModel):
    """Output of the auditor agent - validated by advocate before negotiator uses it."""
    veteran_name: str | None = None
    claim_number: str | None = None
    current_combined_rating: int | None = None
    corrected_combined_rating: int | None = None
    current_monthly_pay_usd: float | None = None
    potential_monthly_pay_usd: float | None = None
    annual_impact_usd: float | None = None
    flags: list[AuditFlag] = Field(default_factory=list)
    tdiu_eligible: bool = False
    pact_act_conditions_found: list[str] = Field(default_factory=list)
    combined_rating_error: bool = False
    auditor_notes: str | None = None


# ---------------------------------------------------------------------------
# Advocate output (debate loop)
# ---------------------------------------------------------------------------

class ValidatedFlag(BaseModel):
    flag: AuditFlag
    upheld: bool
    advocate_note: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class DebateResult(BaseModel):
    """Output of the advocate debate loop."""
    validated_flags: list[ValidatedFlag] = Field(default_factory=list)
    debate_rounds: int = 0
    summary: str | None = None


# ---------------------------------------------------------------------------
# Negotiator / appeal package output
# ---------------------------------------------------------------------------

class AppealPackage(BaseModel):
    veteran_name: str | None = None
    claim_number: str | None = None
    nod_letter_text: str | None = None
    phone_script: str | None = None
    benefits_summary: dict[str, Any] = Field(default_factory=dict)
    va_form_links: list[dict[str, str]] = Field(default_factory=list)
    regional_office: dict[str, str] | None = None
    pdf_path: str | None = None
