"""
Property-based tests for backend/server.py using Hypothesis.

Run with:
    pytest backend/test_server_properties.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# Ensure project root is on sys.path so `from backend.server import app` works
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pytest
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

# Import the Flask app from backend/server.py
from backend.server import app


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def pdf_strategy():
    """Generate small synthetic PDF-like bytes with a .pdf filename."""
    # A minimal valid-looking PDF header followed by arbitrary bytes.
    # The server only checks the filename extension, not the content.
    return st.builds(
        lambda body: (b"%PDF-1.4\n" + body, "test_file.pdf"),
        body=st.binary(min_size=1, max_size=512),
    )


# ---------------------------------------------------------------------------
# Property 1: Upload returns a job_id for any valid file set
# Validates: Requirements 2.1, 2.3
# ---------------------------------------------------------------------------

@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(pdf_files=st.lists(pdf_strategy(), min_size=1, max_size=10))
def test_upload_returns_job_id(pdf_files):
    """
    **Validates: Requirements 2.1, 2.3**

    For any non-empty collection of PDF files sent to POST /api/upload,
    the response status SHALL be 202 and the body SHALL contain a
    non-empty job_id string.
    """
    client = app.test_client()

    data = {}
    file_objects = []
    for i, (content, filename) in enumerate(pdf_files):
        f = io.BytesIO(content)
        file_objects.append(f)
        # Use a unique filename per file to avoid collisions
        unique_name = f"file_{i}.pdf"
        data.setdefault("files", [])
        data["files"].append((f, unique_name))

    response = client.post(
        "/api/upload",
        data=data,
        content_type="multipart/form-data",
    )

    # Close all BytesIO objects
    for f in file_objects:
        f.close()

    assert response.status_code == 202, (
        f"Expected 202, got {response.status_code}: {response.get_json()}"
    )

    body = response.get_json()
    assert body is not None, "Response body should be JSON"
    assert "job_id" in body, f"Response should contain 'job_id', got: {body}"
    assert isinstance(body["job_id"], str), "job_id should be a string"
    assert len(body["job_id"]) > 0, "job_id should be non-empty"


# ---------------------------------------------------------------------------
# Property 2: Empty upload is always rejected
# Validates: Requirements 2.4
# ---------------------------------------------------------------------------

@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
@given(empty=st.just([]))
def test_empty_upload_rejected(empty):
    """
    **Validates: Requirements 2.4**

    For any request to POST /api/upload that contains zero files, the response
    status SHALL be 400 and the body SHALL contain an `error` field.
    """
    client = app.test_client()

    response = client.post(
        "/api/upload",
        data={},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400, (
        f"Expected 400, got {response.status_code}: {response.get_json()}"
    )

    body = response.get_json()
    assert body is not None, "Response body should be JSON"
    assert "error" in body, f"Response should contain 'error' field, got: {body}"


# ---------------------------------------------------------------------------
# Property 3: Oversized file is always rejected
# Validates: Requirements 2.5
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
import backend.server as _server_module


class _SizeFakingStream:
    """
    Wraps a real BytesIO but overrides seek/tell so that seek(0, 2) / tell()
    reports `reported_size` instead of the real buffer length.
    This lets us simulate a large file without allocating the memory.
    """

    def __init__(self, data: bytes, reported_size: int):
        self._buf = io.BytesIO(data)
        self._reported_size = reported_size
        self._at_end = False

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 2:
            # seek-to-end: pretend we're at reported_size + offset
            self._at_end = True
            return self._reported_size + offset
        self._at_end = False
        return self._buf.seek(offset, whence)

    def tell(self) -> int:
        if self._at_end:
            return self._reported_size
        return self._buf.tell()

    def read(self, size: int = -1) -> bytes:
        self._at_end = False
        return self._buf.read(size)

    def readlines(self):
        return self._buf.readlines()

    def __iter__(self):
        return iter(self._buf)


@settings(max_examples=5, suppress_health_check=[HealthCheck.too_slow])
@given(file_size=st.integers(min_value=50 * 1024 * 1024 + 1, max_value=200 * 1024 * 1024))
def test_oversized_file_rejected(file_size):
    """
    **Validates: Requirements 2.5**

    For any single file whose size exceeds 50 MB sent to POST /api/upload,
    the response status SHALL be 413 and the body SHALL contain an `error` field.

    Uses _SizeFakingStream to report `file_size` bytes via seek/tell without
    allocating that memory. The stream wraps a tiny real PDF buffer.
    """
    from werkzeug.datastructures import FileStorage, ImmutableMultiDict
    from flask import request as flask_request
    from backend.server import upload as upload_view

    tiny_pdf = b"%PDF-1.4\n"
    fake_stream = _SizeFakingStream(tiny_pdf, file_size)

    # Use test_request_context to get a real Flask request context,
    # then inject our fake FileStorage directly into request.files.
    with app.test_request_context("/api/upload", method="POST"):
        fs = FileStorage(
            stream=fake_stream,
            filename="large_file.pdf",
            content_type="application/pdf",
            name="files",
        )
        flask_request.files = ImmutableMultiDict([("files", fs)])

        response = upload_view()

    if isinstance(response, tuple):
        resp_obj, status_code = response[0], response[1]
    else:
        resp_obj = response
        status_code = response.status_code

    assert status_code == 413, (
        f"Expected 413 for file_size={file_size}, got {status_code}"
    )

    import json as _json
    body = _json.loads(resp_obj.get_data(as_text=True))
    assert body is not None, "Response body should be JSON"
    assert "error" in body, f"Response should contain 'error' field, got: {body}"


# ---------------------------------------------------------------------------
# Property 6: Unknown job_id always returns 404
# Validates: Requirements 5.3
# ---------------------------------------------------------------------------

from backend.server import jobs as _jobs


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(job_id=st.text(min_size=1))
def test_unknown_job_id_returns_404(job_id):
    """
    **Validates: Requirements 5.3**

    For any string that was never returned as a job_id by POST /api/upload,
    GET /api/result/<that_string> SHALL return HTTP 404.

    Uses a prefix to guarantee the generated id never collides with a real
    UUID issued by the server, and clears the jobs dict before each run.
    """
    # Prefix ensures the id can never match a real UUID-based job_id
    unknown_id = "UNKNOWN_" + job_id

    # Clear the in-memory jobs store so no stale entries interfere
    _jobs.clear()

    client = app.test_client()
    response = client.get(f"/api/result/{unknown_id}")

    assert response.status_code == 404, (
        f"Expected 404 for unknown job_id={unknown_id!r}, "
        f"got {response.status_code}: {response.get_json()}"
    )

    body = response.get_json()
    assert body is not None, "Response body should be JSON"
    assert "error" in body, f"Response should contain 'error' field, got: {body}"


# ---------------------------------------------------------------------------
# Property 4: SSE stream emits all required steps
# Validates: Requirements 3.1, 3.2, 3.3, 3.4
# ---------------------------------------------------------------------------

import json as _json
from unittest.mock import patch as _patch
import backend.server as _server_module2


def _make_mock_pipeline(job_id_holder: list):
    """Return a mock _run_pipeline that injects all 4 required SSE events."""

    def mock_pipeline(job):
        job.events.put(_json.dumps({"step": "parsing_documents", "status": "Parsing uploaded documents..."}))
        job.events.put(_json.dumps({"step": "running_audit", "status": "Running AI audit on your claim..."}))
        job.events.put(_json.dumps({"step": "filling_forms", "status": "Filling VA forms..."}))
        job.status = "complete"
        job.events.put(_json.dumps({"step": "complete", "status": "Audit complete. Redirecting to results..."}))

    return mock_pipeline


@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
@given(pdf_files=st.lists(pdf_strategy(), min_size=1, max_size=3))
def test_sse_emits_required_steps(pdf_files):
    """
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**

    For any completed job, the sequence of `step` values emitted by
    GET /api/stream/<job_id> SHALL contain `parsing_documents`, `running_audit`,
    `filling_forms`, and `complete` (in that order), with no steps omitted.
    """
    client = app.test_client()

    job_id_holder = []

    with _patch("backend.server._run_pipeline", side_effect=_make_mock_pipeline(job_id_holder)):
        # Upload files to get a job_id
        data = {}
        file_objects = []
        for i, (content, filename) in enumerate(pdf_files):
            f = io.BytesIO(content)
            file_objects.append(f)
            data.setdefault("files", [])
            data["files"].append((f, f"file_{i}.pdf"))

        upload_response = client.post(
            "/api/upload",
            data=data,
            content_type="multipart/form-data",
        )

        for f in file_objects:
            f.close()

        assert upload_response.status_code == 202, (
            f"Upload failed: {upload_response.get_json()}"
        )

        job_id = upload_response.get_json()["job_id"]

        # Consume the SSE stream
        stream_response = client.get(f"/api/stream/{job_id}")
        raw = stream_response.get_data(as_text=True)

    # Parse SSE lines: each event line starts with "data: "
    steps = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            payload_str = line[len("data: "):]
            try:
                payload = _json.loads(payload_str)
                if "step" in payload:
                    steps.append(payload["step"])
            except _json.JSONDecodeError:
                pass

    required_steps = ["parsing_documents", "running_audit", "filling_forms", "complete"]

    # Assert all required steps are present
    for step in required_steps:
        assert step in steps, (
            f"Required step '{step}' not found in SSE stream. Got steps: {steps}"
        )

    # Assert they appear in the correct order
    indices = [steps.index(s) for s in required_steps]
    assert indices == sorted(indices), (
        f"Steps are out of order. Expected {required_steps}, got order: "
        f"{[steps[i] for i in sorted(indices)]}, actual positions: {indices}"
    )


# ---------------------------------------------------------------------------
# Property 5: Result endpoint reflects job state
# Validates: Requirements 5.1, 5.2
# ---------------------------------------------------------------------------

import backend.server as _server_module5


def _make_non_completing_pipeline():
    """Return a mock _run_pipeline that puts events but does NOT complete the job."""

    def mock_pipeline(job):
        # Emit some events but intentionally do NOT set job.status = "complete"
        import json as _json2
        job.events.put(_json2.dumps({"step": "parsing_documents", "status": "Parsing uploaded documents..."}))
        job.events.put(_json2.dumps({"step": "running_audit", "status": "Running AI audit on your claim..."}))
        # Pipeline "stalls" here — job remains in "running" state

    return mock_pipeline


_MINIMAL_RESULT = {
    "audit_result": {
        "veteran_name": "Test Veteran",
        "current_combined_rating": 30,
        "corrected_combined_rating": 70,
        "current_monthly_pay_usd": 550.86,
        "potential_monthly_pay_usd": 1803.48,
        "annual_impact_usd": 15031.44,
        "flags": [],
        "auditor_notes": "Test notes",
    },
    "rule_based_report": "",
    "rule_based_triggered": False,
    "filled_form_path": "/tmp/form.pdf",
    "filled_form_paths": ["/tmp/form.pdf"],
    "forms_needed": ["20-0996"],
    "va_form_links": [
        {
            "form_number": "20-0996",
            "filled_path": "/tmp/form.pdf",
            "pdf_url": "https://example.com/form.pdf",
            "fields_found": 10,
            "fields_filled": 5,
        }
    ],
}


@settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
@given(pdf_files=st.lists(pdf_strategy(), min_size=1, max_size=3))
def test_result_reflects_job_state(pdf_files):
    """
    **Validates: Requirements 5.1, 5.2**

    For any job_id, GET /api/result/<job_id> SHALL return 202 while the job is
    running and 200 with the full audit JSON once the job is complete — never
    returning 200 before the pipeline has finished.
    """
    from backend.server import jobs as _live_jobs

    client = app.test_client()

    with _patch("backend.server._run_pipeline", side_effect=_make_non_completing_pipeline()):
        # (a) Upload files to get a job_id
        data = {}
        file_objects = []
        for i, (content, filename) in enumerate(pdf_files):
            f = io.BytesIO(content)
            file_objects.append(f)
            data.setdefault("files", [])
            data["files"].append((f, f"file_{i}.pdf"))

        upload_response = client.post(
            "/api/upload",
            data=data,
            content_type="multipart/form-data",
        )

        for f in file_objects:
            f.close()

        assert upload_response.status_code == 202, (
            f"Upload failed: {upload_response.get_json()}"
        )

        job_id = upload_response.get_json()["job_id"]

        # (b) Immediately check /api/result — job is still "running", expect 202
        result_while_running = client.get(f"/api/result/{job_id}")
        assert result_while_running.status_code == 202, (
            f"Expected 202 while job is running, got {result_while_running.status_code}: "
            f"{result_while_running.get_json()}"
        )
        running_body = result_while_running.get_json()
        assert running_body is not None, "Response body should be JSON"
        # 200 must NEVER be returned before the job is complete
        assert result_while_running.status_code != 200, (
            "200 was returned before job.status == 'complete' — violates Property 5"
        )

        # (c) Manually set job.status = "complete" and job.result = minimal result
        job = _live_jobs[job_id]
        job.result = _MINIMAL_RESULT
        job.status = "complete"

        # (d) Check /api/result again — now expect 200 with full JSON
        result_after_complete = client.get(f"/api/result/{job_id}")
        assert result_after_complete.status_code == 200, (
            f"Expected 200 after job is complete, got {result_after_complete.status_code}: "
            f"{result_after_complete.get_json()}"
        )
        complete_body = result_after_complete.get_json()
        assert complete_body is not None, "Response body should be JSON"
        assert "audit_result" in complete_body, (
            f"Expected 'audit_result' in response, got keys: {list(complete_body.keys())}"
        )
        assert "va_form_links" in complete_body, (
            f"Expected 'va_form_links' in response, got keys: {list(complete_body.keys())}"
        )
