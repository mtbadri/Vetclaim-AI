"""
mock_va_portal/tests/test_server.py — Unit tests for server.py

Tests cover:
  - generate_confirmation_number() format
  - POST /submit-appeal: valid PDF → 201 + confirmation_number
  - POST /submit-appeal: no file → 400
  - POST /submit-appeal: empty filename → 400
  - GET /submissions: empty list on fresh server
  - GET /submissions/<id>/pdf: 404 for unknown ID

Run with:
  pytest mock_va_portal/tests/ -v
"""

import io
import re
import sys
import os
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# Add the project root to sys.path so we can import server.py directly
# without installing the package. This is a common pattern for hackathon
# projects that don't have a formal package structure.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from mock_va_portal.server import app, generate_confirmation_number, submissions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """
    Create a Flask test client with a clean in-memory submissions list.

    We clear the global submissions list before each test so tests don't
    bleed state into each other — each test starts with a fresh server.
    """
    app.config["TESTING"] = True

    # Clear the in-memory store before each test so tests are independent
    submissions.clear()

    with app.test_client() as client:
        yield client


def make_pdf_upload(filename: str = "test_appeal.pdf") -> dict:
    """
    Build a multipart/form-data payload with a minimal fake PDF binary.
    Real PDFs start with %PDF — we use that magic bytes prefix so the
    server treats it as a valid file (it only checks filename, not content).
    """
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content for testing")
    return {"file": (fake_pdf, filename)}


# ---------------------------------------------------------------------------
# generate_confirmation_number() tests
# ---------------------------------------------------------------------------

def test_confirmation_number_format():
    """
    generate_confirmation_number() must return a string matching
    VA-YYYY-NOD-XXXXXX where YYYY is a 4-digit year and XXXXXX is 6 digits.
    Requirement 2.2.
    """
    number = generate_confirmation_number()
    pattern = r"^VA-\d{4}-NOD-\d{6}$"
    assert re.match(pattern, number), (
        f"Confirmation number '{number}' does not match expected pattern {pattern}"
    )


def test_confirmation_number_is_string():
    """generate_confirmation_number() must return a str, not bytes or None."""
    number = generate_confirmation_number()
    assert isinstance(number, str)


def test_confirmation_number_uniqueness():
    """
    Two consecutive calls should (almost certainly) return different numbers.
    The 6-digit random suffix gives 1-in-1,000,000 collision odds — safe for a test.
    """
    a = generate_confirmation_number()
    b = generate_confirmation_number()
    # This could theoretically fail once in a million runs — acceptable for a demo project
    assert a != b, "Two consecutive confirmation numbers were identical (extremely unlikely)"


# ---------------------------------------------------------------------------
# POST /submit-appeal tests
# ---------------------------------------------------------------------------

def test_submit_appeal_valid_pdf_returns_201(client, tmp_path, monkeypatch):
    """
    POST /submit-appeal with a valid PDF file must return HTTP 201 and a
    JSON body containing a 'confirmation_number' field. Requirement 2.2.
    """
    # Redirect file saves to a temp directory so we don't pollute the repo
    monkeypatch.setattr("mock_va_portal.server.UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/submit-appeal",
        data=make_pdf_upload(),
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    body = response.get_json()
    assert "confirmation_number" in body, "Response JSON must include 'confirmation_number'"
    assert re.match(r"^VA-\d{4}-NOD-\d{6}$", body["confirmation_number"])


def test_submit_appeal_valid_pdf_returns_success_true(client, tmp_path, monkeypatch):
    """
    A successful submission must also include 'success': true in the response.
    """
    monkeypatch.setattr("mock_va_portal.server.UPLOAD_DIR", str(tmp_path))

    response = client.post(
        "/submit-appeal",
        data=make_pdf_upload(),
        content_type="multipart/form-data",
    )

    body = response.get_json()
    assert body.get("success") is True


def test_submit_appeal_no_file_returns_400(client):
    """
    POST /submit-appeal with no file field must return HTTP 400.
    Requirement 2.3 — the server must reject malformed requests.
    """
    response = client.post(
        "/submit-appeal",
        data={},  # no 'file' key at all
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    body = response.get_json()
    assert "error" in body


def test_submit_appeal_empty_filename_returns_400(client):
    """
    POST /submit-appeal where the file field has an empty filename must
    return HTTP 400. This guards against browsers sending an empty file input.
    """
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/submit-appeal",
        data={"file": (empty_file, "")},  # empty filename
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    body = response.get_json()
    assert "error" in body


# ---------------------------------------------------------------------------
# GET /submissions tests
# ---------------------------------------------------------------------------

def test_get_submissions_empty_on_fresh_server(client):
    """
    GET /submissions on a fresh server instance (no POSTs yet) must return
    an empty JSON array. Requirement 2.3.
    """
    response = client.get("/submissions")

    assert response.status_code == 200
    body = response.get_json()
    assert body == [], f"Expected empty list, got: {body}"


def test_get_submissions_returns_list(client):
    """GET /submissions must always return a JSON array, never null or an object."""
    response = client.get("/submissions")
    body = response.get_json()
    assert isinstance(body, list)


# ---------------------------------------------------------------------------
# GET /submissions/<id>/pdf tests
# ---------------------------------------------------------------------------

def test_get_pdf_unknown_id_returns_404(client):
    """
    GET /submissions/<id>/pdf for a submission ID that doesn't exist must
    return HTTP 404. Requirement 2.3.
    """
    response = client.get("/submissions/VA-2026-NOD-000000/pdf")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Property-based tests (hypothesis)
# ---------------------------------------------------------------------------

# Feature: mock-va-portal, Property 1: confirmation number format invariant
@given(st.none())
@settings(
    max_examples=100,
    # suppress_health_check for too_slow — generate_confirmation_number() is
    # fast but hypothesis may flag it on slow CI machines
    suppress_health_check=[HealthCheck.too_slow],
)
def test_confirmation_number_format_invariant(_):
    """
    Property 1: Confirmation number format invariant.

    For ANY call to generate_confirmation_number(), the returned string must
    always match the pattern ^VA-\\d{4}-NOD-\\d{6}$.

    This property validates that the format contract holds universally, not
    just for a single example. Hypothesis calls this 100 times to build
    confidence that no edge case (e.g. year rollover, random seed) breaks it.

    Validates: Requirement 2.2
    """
    number = generate_confirmation_number()

    # The full format must match — year is 4 digits, suffix is exactly 6 digits
    pattern = r"^VA-\d{4}-NOD-\d{6}$"
    assert re.match(pattern, number), (
        f"Confirmation number '{number}' violates format invariant. "
        f"Expected pattern: {pattern}"
    )


# Feature: mock-va-portal, Property 2: submit-appeal round trip
@given(
    veteran_name=st.text(min_size=1, max_size=100),
    conditions=st.text(min_size=1, max_size=200),
)
@settings(
    max_examples=100,
    # suppress_health_check for function_scoped_fixture — hypothesis cannot use
    # pytest fixtures with yield (like tmp_path or client) directly, so we
    # manage the Flask app context and temp dir manually inside the test body.
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_submit_appeal_round_trip(veteran_name: str, conditions: str) -> None:
    """
    Property 2: Submit-appeal round trip.

    For ANY valid veteran_name and conditions string, POSTing to /submit-appeal
    must return a confirmation_number that subsequently appears in GET /submissions.

    This validates the full intake pipeline: the server must persist every
    accepted submission so the VA portal frontend can display it. If even one
    submission is accepted (201) but not stored, the veteran's appeal would be
    silently lost — a critical failure for this use case.

    We use tempfile.mkdtemp() instead of pytest's tmp_path fixture because
    hypothesis @given tests run outside pytest's fixture lifecycle. We clean up
    the temp dir after each example to avoid disk accumulation across 100 runs.

    Validates: Requirements 2.2, 2.3
    """
    import tempfile
    import shutil
    from unittest.mock import patch

    # Create a fresh temp dir for each hypothesis example so PDF saves don't
    # accumulate in the real submissions/ folder during property testing.
    temp_dir = tempfile.mkdtemp()

    try:
        # Clear global submissions so each example starts from a known state.
        # This mirrors what the `client` fixture does for unit tests.
        submissions.clear()

        with patch("mock_va_portal.server.UPLOAD_DIR", temp_dir):
            app.config["TESTING"] = True

            with app.test_client() as test_client:
                # Build a minimal fake PDF — the server only checks that a file
                # was provided, not that it's a valid PDF document.
                fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content for property test")

                # POST the appeal with the hypothesis-generated name and conditions
                post_response = test_client.post(
                    "/submit-appeal",
                    data={
                        "file": (fake_pdf, "appeal.pdf"),
                        "veteran_name": veteran_name,
                        "conditions": conditions,
                    },
                    content_type="multipart/form-data",
                )

                # The server must accept the submission — if it rejects valid
                # inputs that's a bug, not a property violation we should skip.
                assert post_response.status_code == 201, (
                    f"Expected 201 for valid submission, got {post_response.status_code}. "
                    f"veteran_name={veteran_name!r}, conditions={conditions!r}"
                )

                post_body = post_response.get_json()
                confirmation_number = post_body.get("confirmation_number")

                assert confirmation_number is not None, (
                    "POST /submit-appeal response must include 'confirmation_number'"
                )

                # Now verify the round trip: the confirmation number must appear
                # in GET /submissions so the VA portal can display it.
                get_response = test_client.get("/submissions")
                assert get_response.status_code == 200

                submission_list = get_response.get_json()
                stored_ids = [s.get("confirmation_number") for s in submission_list]

                assert confirmation_number in stored_ids, (
                    f"confirmation_number '{confirmation_number}' was returned by POST "
                    f"but is missing from GET /submissions. "
                    f"Stored IDs: {stored_ids}"
                )
    finally:
        # Always clean up the temp dir, even if the assertion fails,
        # so 100 hypothesis examples don't leave 100 temp dirs behind.
        shutil.rmtree(temp_dir, ignore_errors=True)
