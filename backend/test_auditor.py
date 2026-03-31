"""
Quick test of the auditor agent.

Run: python backend/test_auditor.py
"""

import json
from agents.auditor_agent import auditor_agent
from schemas import ParsedClaim, ParsedCondition

# Create a sample claim (mimics parser output)
sample_claim = ParsedClaim(
    veteran_name="James Miller",
    claim_number="CLM-2025-001234",
    decision_date="2025-12-01",
    service_era="post-9/11",
    deployment_locations=["Iraq", "Afghanistan"],
    mos="11B (Infantryman)",
    conditions=[
        ParsedCondition(
            condition_name="PTSD",
            diagnostic_code="9411",
            assigned_rating=30,
            body_system="Mental Disorders",
            raw_text_excerpt="Veteran reports near-constant panic, occupational impairment, depression affecting ability to work."
        ),
        ParsedCondition(
            condition_name="Traumatic Brain Injury",
            diagnostic_code="8045",
            assigned_rating=20,
            body_system="Neurological",
            raw_text_excerpt="Balance issues, dizziness, mild memory loss."
        ),
        ParsedCondition(
            condition_name="Asthma",
            diagnostic_code="6602",
            assigned_rating=None,  # Denied
            body_system="Respiratory",
            denial_reason="No service connection established",
            raw_text_excerpt="Wheezing, shortness of breath during exertion."
        ),
    ],
    overall_combined_rating=30,
    raw_decision_text="Veteran rated 30% for PTSD, 20% for TBI...",
)

# Build the input text for the auditor
# (In real pipeline, parser would produce this)
audit_input = f"""
VETERAN: {sample_claim.veteran_name}
CLAIM #: {sample_claim.claim_number}
SERVICE ERA: {sample_claim.service_era}
DEPLOYMENTS: {', '.join(sample_claim.deployment_locations)}

CONDITIONS AND RATINGS:
{json.dumps([c.model_dump() for c in sample_claim.conditions], indent=2)}

STATED COMBINED RATING: {sample_claim.overall_combined_rating}%

SYMPTOMS:
{sample_claim.raw_decision_text}
"""

print("=" * 80)
print("AUDITOR AGENT TEST")
print("=" * 80)
print("\n📋 INPUT CLAIM:")
print(audit_input)
print("\n🔍 RUNNING AUDITOR AGENT...")
print("-" * 80)

# Call the auditor agent
# ADK's agent.generate() takes a prompt and returns response
response = auditor_agent.generate(
    prompt=f"""
Audit this VA disability claim for under-ratings, PACT Act eligibility, TDIU eligibility,
and combined rating errors. Follow the audit process step-by-step using your tools.

{audit_input}

Return a structured JSON audit result.
"""
)

print("\n📊 AUDITOR OUTPUT:")
print("-" * 80)
print(response.text)
