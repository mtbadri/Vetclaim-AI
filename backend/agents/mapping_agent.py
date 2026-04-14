"""
Gemini-powered mapping from logical veteran data keys to PDF AcroForm/XFA field names.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from google import genai
from dotenv import load_dotenv
from pypdf import PdfReader

_BACKEND_DIR = Path(__file__).resolve().parent.parent

_GEMINI_PROMPT = """Match these data points to the best-fit PDF XFA field names from the provided list. Return ONLY a JSON object where the keys are my data points and values are the PDF field names.

CRITICAL RULES:
1. You MUST map names, SSNs, and DOBs to the VETERAN'S fields (e.g., fields containing 'Veterans_First_Name', 'Veterans_SocialSecurityNumber').
2. STRICTLY AVOID mapping to 'Claimants' or 'Representatives' fields unless the data point explicitly asks for it.

Data points: {target_fields_json}

PDF field names (use only names from this list; use null if no good match): {pdf_fields_json}
"""


class VAMappingAgent:
    """Uses Gemini to map semantic data keys to concrete pypdf field names."""

    def __init__(self, backend_dir: str | os.PathLike[str] | None = None) -> None:
        self.backend_dir = os.path.normpath(
            str(backend_dir) if backend_dir is not None else str(_BACKEND_DIR)
        )
        env_path = os.path.join(self.backend_dir, ".env")
        load_dotenv(env_path)
        api_key = os.environ.get("GOOGLE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY is not set. Add it to backend/.env for VAMappingAgent."
            )
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _pdf_field_name_list(pdf_path: str | os.PathLike[str]) -> list[str]:
        path = os.path.normpath(str(pdf_path))
        reader = PdfReader(path)
        fields = reader.get_fields() or {}
        return sorted(fields.keys())

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        raw = text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```\s*$", "", raw)
        return json.loads(raw)

    def get_field_mapping(
        self,
        pdf_path: str | os.PathLike[str],
        target_fields: list[str],
    ) -> dict[str, str | None]:
        """
        Return a dict mapping each target field key to a PDF field name from the document,
        or None when Gemini indicates no match. Values are always members of the PDF's
        field list when not None.
        """
        pdf_fields = self._pdf_field_name_list(pdf_path)
        pdf_set = set(pdf_fields)

        prompt = _GEMINI_PROMPT.format(
            target_fields_json=json.dumps(target_fields, ensure_ascii=False),
            pdf_fields_json=json.dumps(pdf_fields, ensure_ascii=False),
        )

        response = self._client.models.generate_content(
            model="gemini-2.5-flash", 
        contents=prompt
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("VAMappingAgent: empty response from Gemini")

        parsed = self._parse_json_response(text)
        if not isinstance(parsed, dict):
            raise RuntimeError("VAMappingAgent: Gemini returned non-object JSON")

        out: dict[str, str | None] = {}
        for key in target_fields:
            if key not in parsed:
                out[key] = None
                continue
            val = parsed[key]
            if val is None:
                out[key] = None
                continue
            if not isinstance(val, str):
                out[key] = None
                continue
            if val not in pdf_set:
                out[key] = None
                continue
            out[key] = val

        return out
