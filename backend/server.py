"""
VetClaim Backend Server — Flask API on port 5001.

Routes:
  POST /api/upload          — accept PDFs, start pipeline, return job_id
  GET  /api/stream/<job_id> — SSE stream of pipeline progress
  GET  /api/result/<job_id> — return completed audit JSON
  GET  /api/download        — serve a filled PDF by ?path= query param
  GET  /api/status          — health check
"""

from __future__ import annotations

import json
import os
import queue
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import requests
from flask import jsonify
from dotenv import load_dotenv
from google import genai as _genai
from google.genai import types as _genai_types
# ---------------------------------------------------------------------------
# sys.path — ensure project root is importable so agent modules resolve
# ---------------------------------------------------------------------------

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
# Also insert backend dir so `from schemas import ...` works inside agents
_BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BACKEND_DIR))

from flask import Flask, Response, jsonify, request, send_file, send_from_directory, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# In production the frontend is served from the same origin, so CORS is only
# needed for local development.  We still set it permissively so the demo works
# whether running locally or on Render.
CORS(app)

_OUTPUT_DIR = _BACKEND_DIR / "output"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# Reference data (loaded once at startup for chat context)
# ---------------------------------------------------------------------------

_DATA_DIR = _BACKEND_DIR / "data"

def _load_json(name: str) -> dict:
    try:
        return json.loads((_DATA_DIR / name).read_text())
    except Exception:
        return {}

_CFR_DATA        = _load_json("cfr38_part4.json")
_PACT_DATA       = _load_json("pact_act_conditions.json")
_PAY_DATA        = _load_json("va_pay_rates_2026.json")
_COMBINED_DATA   = _load_json("combined_ratings_table.json")

# Gemini client (for /api/chat)
_gemini = _genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# ---------------------------------------------------------------------------
# Job store
# ---------------------------------------------------------------------------

@dataclass
class JobRecord:
    job_id: str
    status: Literal["running", "complete", "error"]
    upload_dir: Path
    result: dict | None = None
    error: str | None = None
    events: queue.Queue = field(default_factory=queue.Queue)


jobs: dict[str, JobRecord] = {}

_JOBS_DIR = _BACKEND_DIR / "jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)

def _persist_job(job: JobRecord) -> None:
    try:
        (_JOBS_DIR / f"{job.job_id}.json").write_text(json.dumps(job.result))
    except Exception:
        pass

def _load_job_result(job_id: str) -> dict | None:
    p = _JOBS_DIR / f"{job_id}.json"
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Pipeline thread
# ---------------------------------------------------------------------------

def _run_pipeline(job: JobRecord) -> None:
    """Background thread: parse → audit → fill forms, emitting SSE events."""

    def emit(step: str, status: str) -> None:
        payload = json.dumps({"step": step, "status": status})
        job.events.put(payload)

    try:
        # Step 1 — Parse documents
        emit("parsing_documents", "Parsing uploaded documents...")
        from agents.parser_agent import VAClaimParser
        parser = VAClaimParser(pdf_dir=str(job.upload_dir))
        parsed_claim = parser.extract_all()

        # Step 2 — Run audit (LLM + rule-based)
        emit("running_audit", "Running AI audit on your claim...")
        from agents.auditor_agent import run_full_audit
        result = run_full_audit(parsed_claim)

        # Step 3 — Form filling happens inside run_full_audit; emit milestone
        emit("filling_forms", "Filling VA forms...")

        # Step 4 — Complete
        job.result = result
        job.status = "complete"
        _persist_job(job)
        emit("complete", "Audit complete. Redirecting to results...")

    except Exception as exc:  # noqa: BLE001
        job.status = "error"
        job.error = str(exc)
        payload = json.dumps({"step": "error", "status": f"Pipeline error: {exc}"})
        job.events.put(payload)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload():
    """Accept PDF files, start pipeline, return job_id with 202."""
    files = request.files.getlist("files")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided"}), 400

    # Validate sizes before saving anything
    for f in files:
        f.stream.seek(0, 2)  # seek to end
        size = f.stream.tell()
        f.stream.seek(0)     # reset
        if size > _MAX_FILE_SIZE:
            return jsonify({"error": "File too large"}), 413

    # Create per-job temp directory
    job_id = str(uuid.uuid4())
    upload_dir = Path(tempfile.mkdtemp(prefix=f"vetclaim_{job_id}_"))

    # Save only PDF files
    saved = 0
    for f in files:
        if f.filename and f.filename.lower().endswith(".pdf"):
            filename = secure_filename(f.filename)
            f.save(str(upload_dir / filename))
            saved += 1

    if saved == 0:
        return jsonify({"error": "No valid PDF files provided"}), 400

    # Create job record and start pipeline thread
    job = JobRecord(job_id=job_id, status="running", upload_dir=upload_dir)
    jobs[job_id] = job

    thread = threading.Thread(target=_run_pipeline, args=(job,), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/api/stream/<job_id>", methods=["GET"])
def stream(job_id: str):
    """SSE stream of pipeline progress for a given job."""
    job = jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        while True:
            try:
                payload = job.events.get(timeout=30)
                yield f"data: {payload}\n\n"
                data = json.loads(payload)
                if data.get("step") in ("complete", "error"):
                    break
            except queue.Empty:
                # Send a keep-alive comment so the connection stays open
                yield ": keep-alive\n\n"
                # If job is done but queue is empty, close
                if job.status in ("complete", "error"):
                    break

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/result/<job_id>", methods=["GET"])
def result(job_id: str):
    """Return audit result JSON, or 202 if still running, or 404 if unknown."""
    job = jobs.get(job_id)
    if job is None:
        saved = _load_job_result(job_id)
        if saved:
            return jsonify(saved), 200
        return jsonify({"error": "Job not found"}), 404

    if job.status == "running":
        return jsonify({"status": "processing"}), 202

    if job.status == "error":
        return jsonify({"error": job.error or "Pipeline failed"}), 500

    return jsonify(job.result), 200


@app.route("/api/download", methods=["GET"])
def download():
    """Serve a filled PDF by ?path= query param; reject path traversal."""
    file_path = request.args.get("path", "")
    if not file_path:
        abort(400)

    abs_path = os.path.realpath(file_path)
    output_dir = os.path.realpath(str(_OUTPUT_DIR))

    if not abs_path.startswith(output_dir + os.sep) and abs_path != output_dir:
        abort(403)

    if not os.path.isfile(abs_path):
        abort(404)

    return send_file(abs_path, as_attachment=True, download_name=os.path.basename(abs_path))


@app.route("/api/status", methods=["GET"])
def status():
    """Health check endpoint."""
    return jsonify({"status": "OK", "service": "VetClaim Backend"}), 200


@app.route("/api/submit-appeal", methods=["POST"])
def submit_appeal():
    """Proxy: forward the veteran's filled PDF(s) to the mock VA portal at localhost:5050."""
    data = request.get_json(force=True) or {}
    job_id = data.get("job_id")
    job = jobs.get(job_id) if job_id else None
    result = (job.result if job else None) or (job_id and _load_job_result(job_id))

    if not result:
        return jsonify({"error": "Job not found or not complete"}), 404
    audit = result.get("audit_result", {})
    veteran_name = audit.get("veteran_name", "Unknown Veteran")
    conditions = ", ".join(
        f.get("condition_name", "") for f in audit.get("flags", []) if f.get("condition_name")
    )

    # Collect filled PDF paths from the job result
    form_links = result.get("va_form_links", [])
    pdf_path = None
    form_numbers = []
    for link in form_links:
        p = link.get("filled_path", "")
        if p and os.path.isfile(p):
            if pdf_path is None:
                pdf_path = p
            form_numbers.append(link.get("form_number", ""))

    if not pdf_path:
        return jsonify({"error": "No filled PDF found for this job"}), 404

    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                "http://localhost:5050/submit-appeal",
                files={"file": (os.path.basename(pdf_path), f, "application/pdf")},
                data={
                    "veteran_name": veteran_name,
                    "conditions": conditions,
                    "forms": ",".join(form_numbers),
                },
                timeout=10,
            )
        resp.raise_for_status()
        return jsonify(resp.json()), resp.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "VA portal unreachable — is it running on port 5050?"}), 502
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
@app.route('/api/call-va', methods=['POST'])
def call_va_rep():
    body = request.get_json(force=True, silent=True) or {}
    phone_number = body.get("phone_number", "").strip()
    veteran_name = body.get("veteran_name", "Veteran").strip() or "Veteran"
    if not phone_number:
        return jsonify({"error": "phone_number is required"}), 400

    url = "https://api.vapi.ai/call/phone"
    headers = {
        "Authorization": f"Bearer {os.getenv('VAPI_PRIVATE_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "assistantId": "efe9791d-f257-40d3-8760-715fdeb669f0",
        "phoneNumberId": "4882efe5-5767-44ef-bb42-4aaf3752dda4",
        "customer": {"number": phone_number},
        "assistantOverrides": {
            "variableValues": {"veteran_name": veteran_name}
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return jsonify({"status": "success", "data": response.json()}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-transcript', methods=['GET'])
def get_transcript():
    url = "https://api.vapi.ai/call?limit=1"
    headers = {"Authorization": f"Bearer {os.getenv('VAPI_PRIVATE_KEY')}"}

    try:
        response = requests.get(url, headers=headers)
        calls = response.json()
        if calls:
            call = calls[0]
            return jsonify({
                "transcript": call.get("transcript", "Transcript is still processing..."),
                "summary": call.get("summary", ""),
                "ended_reason": call.get("endedReason", ""),
                "duration_seconds": call.get("durationSeconds"),
            }), 200
        return jsonify({"transcript": "No calls found.", "summary": ""}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Streaming chat endpoint. Body: { job_id, messages: [{role, content}] }"""
    body = request.get_json(force=True, silent=True) or {}
    job_id   = body.get("job_id", "")
    messages = body.get("messages", [])

    # ── 1. Veteran case context ──────────────────────────────────────────
    job = jobs.get(job_id)
    result = job.result if (job and job.result) else None
    audit  = (result or {}).get("audit_result", {})
    flags  = audit.get("flags", [])

    def fmt_flags(fs):
        lines = []
        for f in fs:
            lines.append(
                f"  - {f.get('condition_name','?')} [{f.get('flag_type','?')}]: "
                f"assigned {f.get('assigned_rating','?')}%, eligible {f.get('eligible_rating','?')}%, "
                f"CFR {f.get('cfr_citation','N/A')} — {f.get('explanation','')}"
            )
        return "\n".join(lines) if lines else "  None"

    veteran_block = f"""Veteran: {audit.get('veteran_name', 'Unknown')}
Current Combined Rating: {audit.get('current_combined_rating', '?')}%
Corrected Combined Rating: {audit.get('corrected_combined_rating', '?')}%
Current Monthly Pay: ${audit.get('current_monthly_pay_usd', '?')}
Potential Monthly Pay: ${audit.get('potential_monthly_pay_usd', '?')}
Annual Impact: ${audit.get('annual_impact_usd', '?')}
TDIU Eligible: {audit.get('tdiu_eligible', 'Unknown')}
PACT Act Conditions Found: {', '.join(audit.get('pact_act_conditions_found', [])) or 'None'}
Audit Flags:
{fmt_flags(flags)}
Auditor Notes: {audit.get('auditor_notes', 'N/A')}
Rule-Based Report: {(result or {}).get('rule_based_report', 'N/A')}""" if result else "No audit data available for this session."

    # ── 2. Call transcript (best-effort) ────────────────────────────────
    transcript_block = "No call transcript available."
    try:
        r = requests.get(
            "https://api.vapi.ai/call?limit=1",
            headers={"Authorization": f"Bearer {os.getenv('VAPI_PRIVATE_KEY')}"},
            timeout=5,
        )
        calls = r.json()
        if calls:
            t = calls[0].get("transcript", "")
            s = calls[0].get("summary", "")
            if t or s:
                transcript_block = ""
                if s:
                    transcript_block += f"Summary: {s}\n\n"
                if t:
                    transcript_block += f"Full transcript:\n{t}"
    except Exception:
        pass

    # ── 3. CFR reference — only codes in this veteran's flags ────────────
    flag_codes = {str(f.get("diagnostic_code", "")) for f in flags if f.get("diagnostic_code")}
    cfr_lines = []
    for code, entry in _CFR_DATA.items():
        if code in flag_codes or entry.get("condition","").lower() in [f.get("condition_name","").lower() for f in flags]:
            cfr_lines.append(
                f"  DC {code} — {entry.get('condition','?')} | Max: {entry.get('max_rating','?')}% | "
                f"{entry.get('cfr_section','?')}"
            )
    cfr_block = "\n".join(cfr_lines) if cfr_lines else "No matching CFR codes found for this veteran's conditions."

    # ── 4. PACT Act summary ──────────────────────────────────────────────
    pact_lines = []
    for cat_key, cat in _PACT_DATA.get("exposure_categories", {}).items():
        conditions = cat.get("presumptive_conditions", [])
        names = [str(c.get("name", c)) if isinstance(c, dict) else str(c) for c in conditions[:8]]
        pact_lines.append(f"  {cat.get('label', cat_key)}: {', '.join(names)}" + (" ..." if len(conditions) > 8 else ""))
    pact_block = "\n".join(pact_lines) if pact_lines else "N/A"

    # ── 5. Pay rates ─────────────────────────────────────────────────────
    pay_block = json.dumps(_PAY_DATA.get("veteran_alone", {}), indent=2)

    # ── 6. Combined rating table ─────────────────────────────────────────
    combined_block = json.dumps(_COMBINED_DATA, indent=2)[:2000]  # cap at 2k chars

    system_prompt = f"""You are an expert VA disability claims advisor with deep knowledge of 38 CFR Part 4, the PACT Act, VA combined rating math, TDIU eligibility, and the VA appeals process.

You have the complete audit results for this veteran's specific case. You can:
- Explain findings in plain language the veteran can understand
- Answer questions about VA regulations, rating criteria, and appeal options
- Discuss the VA call transcript and interpret what representatives said
- Help draft appeal language, nexus statement talking points, and NOD arguments
- Be honest about uncertainty — do not overstate what you know

=== VETERAN CASE ===
{veteran_block}

=== VA CALL TRANSCRIPT ===
{transcript_block}

=== CFR PART 4 (relevant to this case) ===
{cfr_block}

=== VA PAY RATES 2026 (veteran alone) ===
{pay_block}

=== PACT ACT PRESUMPTIVE CONDITIONS ===
{pact_block}

=== COMBINED RATING TABLE ===
{combined_block}

Be empathetic — these are veterans navigating a complex bureaucratic system. Cite specific CFR sections when relevant. Keep responses clear and actionable."""

    # ── Convert messages to Gemini format ────────────────────────────────
    gemini_contents = []
    for m in messages[-20:]:  # cap at 20 messages
        role = "model" if m.get("role") == "assistant" else "user"
        gemini_contents.append(
            _genai_types.Content(role=role, parts=[_genai_types.Part(text=m.get("content", ""))])
        )

    def generate():
        try:
            for chunk in _gemini.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=gemini_contents,
                config=_genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1024,
                ),
            ):
                if chunk.text:
                    yield f"data: {json.dumps(chunk.text)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps(f'Error: {exc}')}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Static file serving (production: frontend/dist + testcases)
# ---------------------------------------------------------------------------

_DIST_DIR     = _PROJECT_ROOT / "frontend" / "dist"
_TESTCASE_DIR = _PROJECT_ROOT / "testcases"


@app.route("/testcases/<veteran>/<path:filename>")
def serve_testcase(veteran: str, filename: str):
    """Serve a test-case PDF so the frontend demo buttons can load real files."""
    # Guard against path traversal
    safe = Path(filename)
    if ".." in safe.parts or ".." in Path(veteran).parts:
        abort(403)
    full = _TESTCASE_DIR / veteran / safe
    if not full.is_file():
        abort(404)
    return send_file(str(full), mimetype="application/pdf")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):
    """Serve the React SPA for any non-API route (production mode)."""
    if not _DIST_DIR.exists():
        # Dev mode: frontend is served by Vite on port 5173
        abort(404)
    candidate = _DIST_DIR / path
    if path and candidate.exists() and candidate.is_file():
        return send_from_directory(str(_DIST_DIR), path)
    # SPA fallback — return index.html for all unknown paths
    return send_from_directory(str(_DIST_DIR), "index.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = not os.environ.get("PORT")   # debug=False when PORT is set (production)
    app.run(debug=debug, port=port, host="0.0.0.0")