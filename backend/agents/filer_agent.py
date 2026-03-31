"""
VA Form download and PDF fill.

Strategy: strip the XFA layer so the PDF falls back to AcroForm rendering,
then fill using exact AcroForm field paths. Result is viewable in Preview,
Chrome, Firefox, and every standard PDF viewer.

Supports: 20-0996 (HLR), 20-0995 (Supplemental), 21-526EZ (New Claim), 21-8940 (TDIU).
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

import requests
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

_BACKEND_DIR = Path(__file__).resolve().parent.parent

VA_FORMS_API_BASE = "https://api.va.gov/forms_api/v1/forms/{form_number}"
LIGHTHOUSE_FORMS_BASE = "https://api.va.gov/services/va_forms/v0/forms/{form_number}"

FALLBACK_FORM_URLS: dict[str, str] = {
    "20-0996":  "https://www.vba.va.gov/pubs/forms/VBA-20-0996-ARE.pdf",
    "20-0995":  "https://www.vba.va.gov/pubs/forms/VBA-20-0995-ARE.pdf",
    "21-526EZ": "https://www.vba.va.gov/pubs/forms/VBA-21-526EZ-ARE.pdf",
    "21-8940":  "https://www.vba.va.gov/pubs/forms/VBA-21-8940-ARE.pdf",
}

# Exact AcroForm dot-path field names, confirmed from reader.get_fields() on each blank PDF.
# Maps semantic veteran_data keys → full PDF field path.
ACROFORM_FIELD_MAPS: dict[str, dict[str, str]] = {
    "20-0996": {
        "first_name":    "form1[0].#subform[2].Veterans_First_Name[0]",
        "last_name":     "form1[0].#subform[2].Veterans_Last_Name[0]",
        "ssn_1":         "form1[0].#subform[2].Veterans_SocialSecurityNumber_FirstThreeNumbers[0]",
        "ssn_2":         "form1[0].#subform[2].Veterans_SocialSecurityNumber_SecondTwoNumbers[0]",
        "ssn_3":         "form1[0].#subform[2].Veterans_SocialSecurityNumber_LastFourNumbers[0]",
        "dob_month":     "form1[0].#subform[2].DOBmonth[0]",
        "dob_day":       "form1[0].#subform[2].DOBday[0]",
        "dob_year":      "form1[0].#subform[2].DOByear[0]",
        "phone_area":    "form1[0].#subform[2].Telephone_Number_Area_Code[0]",
        "phone_mid":     "form1[0].#subform[2].Telephone_Middle_Three_Numbers[0]",
        "phone_last":    "form1[0].#subform[2].Telephone_Last_Four_Numbers[0]",
        "address_street": "form1[0].#subform[2].CurrentMailingAddress_NumberAndStreet[0]",
        "address_city":  "form1[0].#subform[2].CurrentMailingAddress_City[0]",
        "address_state": "form1[0].#subform[2].CurrentMailingAddress_StateOrProvince[0]",
        "address_zip":   "form1[0].#subform[2].CurrentMailingAddress_ZIPOrPostalCode_FirstFiveNumbers[0]",
        "issue":         "form1[0].#subform[3].SPECIFICISSUE1[0]",
        "date_month":    "form1[0].#subform[3].Date_Month[0]",
        "date_day":      "form1[0].#subform[3].Date_Day[0]",
        "date_year":     "form1[0].#subform[3].Date_Year[0]",
        "sign_month":    "form1[0].#subform[4].Date_Signed_Month[0]",
        "sign_day":      "form1[0].#subform[4].Date_Signed_Day[0]",
        "sign_year":     "form1[0].#subform[4].Date_Signed_Year[0]",
    },
    "20-0995": {
        "first_name":    "form1[0].#subform[3].VeteransFirstName[0]",
        "last_name":     "form1[0].#subform[3].VeteransLastName[0]",
        "ssn_1":         "form1[0].#subform[3].Veterans_SocialSecurityNumber_FirstThreeNumbers[0]",
        "ssn_2":         "form1[0].#subform[3].Veterans_SocialSecurityNumber_SecondTwoNumbers[0]",
        "ssn_3":         "form1[0].#subform[3].Veterans_SocialSecurityNumber_LastFourNumbers[0]",
        "dob_month":     "form1[0].#subform[3].DOBmonth[0]",
        "dob_day":       "form1[0].#subform[3].DOBday[0]",
        "dob_year":      "form1[0].#subform[3].DOByear[0]",
        "phone_area":    "form1[0].#subform[3].Telephone_Number_AreaCode[0]",
        "phone_mid":     "form1[0].#subform[4].Telephone_Middle_Three_Numbers[0]",
        "phone_last":    "form1[0].#subform[4].Telephone_Last_Four_Numbers[0]",
        "address_street": "form1[0].#subform[3].MailingAddress_NumberAndStreet[0]",
        "address_city":  "form1[0].#subform[3].MailingAddress_City[0]",
        "address_state": "form1[0].#subform[3].MailingAddress_StateOrProvince[0]",
        "address_zip":   "form1[0].#subform[3].MailingAddress_ZIPOrPostalCode_FirstFiveNumbers[0]",
        "issue":         "form1[0].#subform[4].SPECIFICISSUE2[0]",
        "date_month":    "form1[0].#subform[4].Date_Of_VA_Decision_Notice_Month[0]",
        "date_day":      "form1[0].#subform[4].Date_Day[0]",
        "date_year":     "form1[0].#subform[4].Date_Year[0]",
        "sign_month":    "form1[0].#subform[6].Date_Signed_Month[0]",
        "sign_day":      "form1[0].#subform[6].Date_Signed_Day[0]",
        "sign_year":     "form1[0].#subform[6].Date_Signed_Year[0]",
    },
    "21-526EZ": {
        "first_name":    "F[0].Page_10[0].Veteran_Service_Member_First_Name[0]",
        "last_name":     "F[0].Page_10[0].Veteran_Service_Member_Last_Name[0]",
        "ssn_1":         "F[0].Page_10[0].SocialSecurityNumber_FirstThreeNumbers[0]",
        "ssn_2":         "F[0].Page_10[0].SocialSecurityNumber_SecondTwoNumbers[0]",
        "ssn_3":         "F[0].Page_10[0].SocialSecurityNumber_LastFourNumbers[0]",
        "dob_month":     "F[0].Page_10[0].Date_Of_Birth_Month[0]",
        "dob_day":       "F[0].Page_10[0].Date_Of_Birth_Day[0]",
        "dob_year":      "F[0].Page_10[0].Date_Of_Birth_Year[0]",
        "phone_area":    "F[0].Page_10[0].Daytime_Phone_Number_Area_Code[0]",
        "phone_mid":     "F[0].Page_10[0].Telephone_Middle_Three_Numbers[0]",
        "phone_last":    "F[0].Page_10[0].Telephone_Last_Four_Numbers[0]",
        "address_street": "F[0].Page_10[0].CurrentMailingAddress_NumberAndStreet[0]",
        "address_city":  "F[0].Page_10[0].CurrentMailingAddress_City[0]",
        "address_state": "F[0].Page_10[0].CurrentMailingAddress_StateOrProvince[0]",
        "address_zip":   "F[0].Page_10[0].CurrentMailingAddress_ZIPOrPostalCode_FirstFiveNumbers[0]",
        "issue":         "F[0].#subform[10].CURRENTDISABILITY[0]",
        "sign_month":    "F[0].#subform[12].Date_Signed_Month[0]",
        "sign_day":      "F[0].#subform[12].Date_Signed_Day[0]",
        "sign_year":     "F[0].#subform[12].Date_Signed_Year[0]",
    },
    "21-8940": {
        "first_name":    "form1[0].#subform[0].VeteransFirstName[0]",
        "last_name":     "form1[0].#subform[0].VeteransLastName[0]",
        "ssn_1":         "form1[0].#subform[0].SSNFirstThreeNumbers[0]",
        "ssn_2":         "form1[0].#subform[0].SSNSecondTwoNumbers[0]",
        "ssn_3":         "form1[0].#subform[0].SSNLastFourNumbers[0]",
        "phone_area":    "form1[0].#subform[0].AreaCode[0]",
        "phone_mid":     "form1[0].#subform[0].FirstThreeNumbers[0]",
        "phone_last":    "form1[0].#subform[0].LastFourNumbers[0]",
        "address_street": "form1[0].#subform[0].CurrentMailingAddress_NumberAndStreet[0]",
        "address_city":  "form1[0].#subform[0].CurrentMailingAddress_City[0]",
        "address_state": "form1[0].#subform[0].CurrentMailingAddress_StateOrProvince[0]",
        "address_zip":   "form1[0].#subform[0].CurrentMailingAddress_ZIPOrPostalCode_FirstFiveNumbers[0]",
        "issue":         "form1[0].#subform[0].Service_Connected_Disability[0]",
    },
}

# Legacy names kept for backwards-compat
BLANK_PDF_NAME = "blank_20_0996.pdf"
FILLED_PDF_NAME = "james_miller_ready_to_file_appeal.pdf"

_HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "VAClaimAuditor/1.0 (hackathon; +https://www.va.gov)",
}


class VAFormFiler:
    """Download VA forms and fill them via AcroForm (XFA stripped for universal rendering)."""

    def __init__(self, backend_dir: str | Path | os.PathLike[str] | None = None) -> None:
        self.backend_dir = os.path.normpath(
            str(backend_dir) if backend_dir is not None else str(_BACKEND_DIR)
        )

    def _get_form_pdf_url_from_api(self, form_number: str = "20-0996") -> str:
        primary_url = VA_FORMS_API_BASE.format(form_number=form_number)
        try:
            r = requests.get(primary_url, headers=_HTTP_HEADERS, timeout=60)
            if r.ok:
                payload = r.json()
                url = payload.get("data", {}).get("attributes", {}).get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
        except Exception:
            pass

        api_key = os.environ.get("VA_FORMS_API_KEY", "").strip()
        if api_key:
            try:
                lighthouse_url = LIGHTHOUSE_FORMS_BASE.format(form_number=form_number)
                r2 = requests.get(
                    lighthouse_url,
                    headers={**_HTTP_HEADERS, "apikey": api_key},
                    timeout=60,
                )
                if r2.ok:
                    payload = r2.json()
                    url = payload.get("data", {}).get("attributes", {}).get("url")
                    if isinstance(url, str) and url.startswith("http"):
                        return url
            except Exception:
                pass

        return FALLBACK_FORM_URLS.get(form_number, FALLBACK_FORM_URLS["20-0996"])

    def _strip_xfa(self, writer: PdfWriter) -> None:
        """Remove the /XFA entry from /AcroForm so viewers use AcroForm rendering."""
        root = writer._root_object
        acroform_ref = root.get("/AcroForm")
        if acroform_ref is None:
            return
        acroform = acroform_ref.get_object()
        if "/XFA" in acroform:
            del acroform[NameObject("/XFA")]

    @staticmethod
    def _patch_appearance_streams(pdf_path: str) -> None:
        """
        Fix pypdf's missing 'n' operator after 'W' in form XObject appearance streams.

        pypdf generates:  W\n BT
        PDF spec requires: W n\n BT   (the 'n' discards the clipping path so text shows)

        Without 'n', Preview and Chrome skip rendering the text entirely.
        We patch every Form XObject in-place after writing.
        """
        reader = PdfReader(pdf_path)
        writer = PdfWriter(clone_from=reader)

        _W_BT = re.compile(rb'\bW\b(\s+)BT\b')

        for obj in writer._objects:
            try:
                resolved = obj.get_object() if hasattr(obj, 'get_object') else obj
            except Exception:
                continue

            if not hasattr(resolved, 'get'):
                continue
            if resolved.get('/Subtype') != '/Form':
                continue

            # Decode the stream
            try:
                raw = resolved.get_data()
            except Exception:
                continue

            patched = _W_BT.sub(rb'W\1n \nBT', raw)
            if patched == raw:
                continue

            resolved.set_data(patched)

        with open(pdf_path, "wb") as f:
            writer.write(f)

    def _fill_acroform(
        self, pdf_path: str, veteran_data: dict[str, Any], form_number: str
    ) -> tuple[int, int]:
        """
        Strip XFA, fill AcroForm fields with veteran data, write back to pdf_path.

        Returns:
            (fields_found, fields_filled) counts.
        """
        field_map = ACROFORM_FIELD_MAPS.get(form_number, {})
        fields_found = len(field_map)

        reader = PdfReader(pdf_path)
        writer = PdfWriter(clone_from=reader)

        self._strip_xfa(writer)
        writer.set_need_appearances_writer(True)

        # Build updates dict — only include keys that have a non-empty value
        updates: dict[str, str] = {}
        for data_key, pdf_field in field_map.items():
            value = veteran_data.get(data_key)
            if value:
                updates[pdf_field] = str(value)

        fields_filled = len(updates)

        if updates:
            for page in writer.pages:
                writer.update_page_form_field_values(page, updates)

        with open(pdf_path, "wb") as f:
            writer.write(f)

        # Patch missing 'n' operator so appearance streams render in Preview/Chrome
        if updates:
            self._patch_appearance_streams(pdf_path)

        return fields_found, fields_filled

    def download_and_fill_hlr(
        self, veteran_data: dict[str, Any], form_number: str = "20-0996"
    ) -> tuple[str, int, int]:
        """
        Download a blank VA form, fill it via AcroForm, save to output/.

        Args:
            veteran_data: Dict with semantic keys (first_name, last_name, issue, etc.).
            form_number: VA form number (20-0996, 20-0995, 21-526EZ, 21-8940).

        Returns:
            (filled_path, fields_found, fields_filled)
        """
        pdf_url = self._get_form_pdf_url_from_api(form_number)
        pdf_resp = requests.get(pdf_url, timeout=120)
        pdf_resp.raise_for_status()

        safe_form = form_number.replace("-", "_")
        blank_name = f"blank_{safe_form}.pdf"
        blank_path = os.path.join(self.backend_dir, blank_name)

        out_dir = os.path.join(self.backend_dir, "output")
        os.makedirs(out_dir, exist_ok=True)

        first = (veteran_data.get("first_name") or "veteran").lower().replace(" ", "_")
        last = (veteran_data.get("last_name") or "").lower().replace(" ", "_")
        name_part = f"{first}_{last}" if last else first
        filled_name = f"{name_part}_{safe_form}_filled.pdf"
        filled_path = os.path.join(out_dir, filled_name)

        # Save blank, copy to filled path, then fill in-place
        with open(blank_path, "wb") as f:
            f.write(pdf_resp.content)

        shutil.copy2(blank_path, filled_path)
        fields_found, fields_filled = self._fill_acroform(filled_path, veteran_data, form_number)

        return filled_path, fields_found, fields_filled
