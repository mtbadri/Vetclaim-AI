"""
Extract text from VA claim PDFs (personal statement, decision letter, DBQ, C&P exam)
and emit structured ParsedClaim Pydantic model. Requires pdfplumber.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from backend.schemas import ParsedClaim, ParsedCondition


class VAClaimParser:
    """Parse VA disability claim PDFs into structured ParsedClaim data."""

    def __init__(self, pdf_dir: str | Path | None = None) -> None:
        self.pdf_dir = Path(pdf_dir) if pdf_dir is not None else Path.cwd()

    def _classify_files(self) -> dict[str, Path | list[Path] | None]:
        """
        Scan all PDFs in pdf_dir and classify by filename keywords.

        Returns:
            {
                "decision": Path | None,
                "statement": Path | None,
                "cp_exam": Path | None,
                "dbqs": list[Path],
            }
        """
        classified = {"decision": None, "statement": None, "cp_exam": None, "dbqs": []}

        for pdf_path in sorted(self.pdf_dir.glob("*.pdf")):
            name_lower = pdf_path.stem.lower()

            # DBQ wins over all other classifications
            if "dbq" in name_lower:
                classified["dbqs"].append(pdf_path)
            elif "decision" in name_lower:
                classified["decision"] = pdf_path
            elif "statement" in name_lower or "personal" in name_lower:
                classified["statement"] = pdf_path
            elif ("cp" in name_lower or "exam" in name_lower) and "dbq" not in name_lower:
                classified["cp_exam"] = pdf_path

        return classified

    def _extract_plain_text(self, pdf_path: Path) -> dict[str, Any]:
        """Extract plain text from a PDF, page by page."""
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        parts: list[str] = []
        page_chars: list[int] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                parts.append(t)
                page_chars.append(len(t))

        full = "\n\n".join(parts)
        return {
            "filename": pdf_path.name,
            "path": str(pdf_path.resolve()),
            "page_count": len(parts),
            "text": full,
            "chars_per_page": page_chars,
        }

    def _extract_layout_text(self, pdf_path: Path) -> dict[str, Any]:
        """Extract layout-preserving text from a PDF, page by page."""
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        layout_parts: list[str] = []
        page_layout_chars: list[int] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                block = page.extract_text(layout=True) or ""
                layout_parts.append(block)
                page_layout_chars.append(len(block))

        layout_full = "\n\n".join(layout_parts)
        return {
            "filename": pdf_path.name,
            "path": str(pdf_path.resolve()),
            "page_count": len(layout_parts),
            "layout_text": layout_full,
            "layout_chars_per_page": page_layout_chars,
        }

    def detect_staggering_unsteady_in_layout(self, layout_text: str) -> dict[str, str]:
        """
        Check layout-preserving text for 'Staggering' or 'Unsteady' (word-level, case-insensitive).
        Returns status strings DETECTED / NOT_DETECTED per keyword.
        """
        stagger_re = re.compile(r"\bStaggering\b", re.IGNORECASE)
        unsteady_re = re.compile(r"\bUnsteady\b", re.IGNORECASE)
        return {
            "staggering": "DETECTED" if stagger_re.search(layout_text) else "NOT_DETECTED",
            "unsteady": "DETECTED" if unsteady_re.search(layout_text) else "NOT_DETECTED",
        }

    def extract_personal_statement(self, pdf_path: Path | None) -> dict[str, Any] | None:
        """Extract personal statement PDF, or None if not found."""
        if pdf_path is None:
            return None
        return self._extract_plain_text(pdf_path)

    def extract_decision_letter(self, pdf_path: Path | None) -> dict[str, Any] | None:
        """Extract decision letter PDF, or None if not found."""
        if pdf_path is None:
            return None
        return self._extract_plain_text(pdf_path)

    def extract_cp_exam(self, pdf_path: Path | None) -> dict[str, Any] | None:
        """Extract C&P exam PDF, or None if not found."""
        if pdf_path is None:
            return None
        return self._extract_plain_text(pdf_path)

    def extract_dbqs(self, dbq_paths: list[Path]) -> dict[str, Any] | None:
        """Extract all DBQ PDFs (multiple), concatenate texts, merge gait flags."""
        if not dbq_paths:
            return None

        all_layout_texts: list[str] = []
        all_filenames: list[str] = []
        all_flags = {"staggering": "NOT_DETECTED", "unsteady": "NOT_DETECTED"}

        for dbq_path in dbq_paths:
            data = self._extract_layout_text(dbq_path)
            all_filenames.append(data["filename"])
            all_layout_texts.append(data["layout_text"])

            # Merge flags: DETECTED wins
            flags = self.detect_staggering_unsteady_in_layout(data["layout_text"])
            if flags.get("staggering") == "DETECTED":
                all_flags["staggering"] = "DETECTED"
            if flags.get("unsteady") == "DETECTED":
                all_flags["unsteady"] = "DETECTED"

        layout_full = "\n\n--- NEXT DBQ ---\n\n".join(all_layout_texts)

        return {
            "filenames": all_filenames,
            "paths": [str(p.resolve()) for p in dbq_paths],
            "page_count": len(dbq_paths),
            "layout_text": layout_full,
            "gait_keyword_flags": all_flags,
        }

    def _extract_veteran_name_from_text(self, text: str | None) -> str | None:
        """
        Extract veteran name from decision letter text.
        Looks for patterns like "Dear [Name]," or "Veteran: [Name]".
        """
        if not text:
            return None

        # Try "Dear John Smith," pattern
        match = re.search(r"Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,", text)
        if match:
            return match.group(1)

        # Try "Veteran: John Smith" pattern
        match = re.search(r"Veteran[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
        if match:
            return match.group(1)

        # Try "Name: John Smith" pattern
        match = re.search(r"(?:Veteran\s+)?[Nn]ame[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text)
        if match:
            return match.group(1)

        return None

    def extract_all(self) -> ParsedClaim:
        """
        Extract all documents and return structured ParsedClaim.
        """
        files = self._classify_files()

        # Extract each document type
        decision_data = self.extract_decision_letter(files["decision"])
        statement_data = self.extract_personal_statement(files["statement"])
        cp_exam_data = self.extract_cp_exam(files["cp_exam"])
        dbq_data = self.extract_dbqs(files["dbqs"])

        # Get raw texts
        raw_decision_text = decision_data["text"] if decision_data else None
        raw_statement_text = statement_data["text"] if statement_data else None
        raw_cp_text = cp_exam_data["text"] if cp_exam_data else None

        # Combine statement + CP exam for raw_statement_text field
        combined_statement = None
        if raw_statement_text and raw_cp_text:
            combined_statement = f"{raw_statement_text}\n\n--- CP EXAM ---\n\n{raw_cp_text}"
        elif raw_statement_text:
            combined_statement = raw_statement_text
        elif raw_cp_text:
            combined_statement = raw_cp_text

        raw_dbq_text = dbq_data["layout_text"] if dbq_data else None
        gait_flags = dbq_data["gait_keyword_flags"] if dbq_data else {}

        # Extract veteran name from decision letter
        veteran_name = self._extract_veteran_name_from_text(raw_decision_text)

        # Build ParsedClaim
        return ParsedClaim(
            veteran_name=veteran_name,
            raw_decision_text=raw_decision_text,
            raw_statement_text=combined_statement,
            raw_dbq_text=raw_dbq_text,
            gait_keyword_flags=gait_flags,
            conditions=[],  # LLM fills this from raw text
        )

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize extract_all() to JSON string."""
        parsed = self.extract_all()
        return json.dumps(parsed.model_dump(), indent=indent, ensure_ascii=False)


def main() -> None:
    base = Path(__file__).resolve().parent.parent
    parser = VAClaimParser(pdf_dir=base)
    print(parser.to_json())


if __name__ == "__main__":
    main()
