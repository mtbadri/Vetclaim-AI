"""
test_html_static.py — Static validation tests for the mock VA portal HTML/CSS/JS files.

WHY these tests exist:
  The mock VA portal must look and behave like a real VA.gov page for the demo to be
  convincing. These tests catch regressions where someone accidentally removes the
  disclaimer, breaks the conditions table, or introduces an external stylesheet
  dependency that would fail in an offline demo environment.

Tests are intentionally static (no server required) — they parse the files directly.
"""

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# Go up two levels: tests/ -> mock_va_portal/
PORTAL_DIR = Path(__file__).parent.parent

INDEX_HTML = PORTAL_DIR / "index.html"
CONFIRMATION_HTML = PORTAL_DIR / "confirmation.html"
STYLE_CSS = PORTAL_DIR / "style.css"
VA_API_JS = PORTAL_DIR / "va_api.js"


# ---------------------------------------------------------------------------
# Minimal HTML parser helpers
# ---------------------------------------------------------------------------

class _TextCollector(HTMLParser):
    """Collect all visible text content from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)


class _LinkCollector(HTMLParser):
    """Collect all <link> tag attributes from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "link":
            self.links.append(dict(attrs))


class _TableRowCounter(HTMLParser):
    """
    Count <tr> elements that appear inside a <tbody>.

    WHY: We need to verify the conditions table has exactly 6 rows — one per
    rated condition. If a row is accidentally deleted or duplicated, the demo
    story breaks (we claim 6 conditions, 2 denied).
    """

    def __init__(self) -> None:
        super().__init__()
        self._in_tbody = False
        self.tbody_tr_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self.tbody_tr_count += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False


class _ClassCounter(HTMLParser):
    """Count elements that have a specific CSS class in their class attribute."""

    def __init__(self, target_class: str) -> None:
        super().__init__()
        self.target_class = target_class
        self.count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr_dict = dict(attrs)
        classes = attr_dict.get("class", "") or ""
        # Split on whitespace so we match whole class names, not substrings
        if self.target_class in classes.split():
            self.count += 1


# ---------------------------------------------------------------------------
# Parametrize helpers
# ---------------------------------------------------------------------------

HTML_FILES = [
    pytest.param(INDEX_HTML, id="index.html"),
    pytest.param(CONFIRMATION_HTML, id="confirmation.html"),
]


# ---------------------------------------------------------------------------
# P6 — Disclaimer present on all pages
# Feature: mock-va-portal, Property 6: disclaimer present on all pages
# ---------------------------------------------------------------------------

# The exact disclaimer text required by the project overview.
# Uses an em dash (—, U+2014) — must match the HTML source exactly.
DISCLAIMER_TEXT = (
    "Demo mock portal \u2014 VetClaim AI HackUSF 2026. "
    "Not affiliated with the U.S. Department of Veterans Affairs."
)


@pytest.mark.parametrize("html_path", HTML_FILES)
def test_disclaimer_present_on_all_pages(html_path: Path) -> None:
    """
    **Validates: Requirements 1.8, 2.9, 8.1**

    WHY: Every page of the mock portal must carry the disclaimer so judges and
    veterans clearly understand this is a demo, not the real VA.gov. Forgetting
    the disclaimer on even one page could cause confusion during the live demo.

    Property 6: Disclaimer present on all pages.
    NOTE: This is a static check (pytest parametrize), not a hypothesis property
    test — the "property" here means a correctness property, not a
    hypothesis-style generated test.
    """
    # Tag comment: # Feature: mock-va-portal, Property 6: disclaimer present on all pages
    raw_html = html_path.read_text(encoding="utf-8")

    parser = _TextCollector()
    parser.feed(raw_html)
    page_text = parser.get_text()

    assert DISCLAIMER_TEXT in page_text, (
        f"{html_path.name} footer must contain the disclaimer text.\n"
        f"Expected: {DISCLAIMER_TEXT!r}\n"
        f"Tip: check the <footer> element for the .va-footer__disclaimer paragraph."
    )


# ---------------------------------------------------------------------------
# P7 — No external stylesheet dependencies
# Feature: mock-va-portal, Property 7: no external stylesheet dependencies
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("html_path", HTML_FILES)
def test_no_external_stylesheets(html_path: Path) -> None:
    """
    **Validates: Requirements 6.2**

    WHY: The demo must run offline (no internet at the hackathon venue is a
    real risk). Any <link rel="stylesheet"> pointing to an external CDN would
    break the visual design if the network is unavailable.

    Property 7: No external stylesheet dependencies.
    NOTE: This is a static check (pytest parametrize), not a hypothesis property
    test — the "property" here means a correctness property, not a
    hypothesis-style generated test.
    """
    # Tag comment: # Feature: mock-va-portal, Property 7: no external stylesheet dependencies
    raw_html = html_path.read_text(encoding="utf-8")

    parser = _LinkCollector()
    parser.feed(raw_html)

    for link_attrs in parser.links:
        rel = link_attrs.get("rel", "")
        href = link_attrs.get("href", "") or ""
        if rel == "stylesheet":
            assert not href.startswith("http://") and not href.startswith("https://"), (
                f"{html_path.name} has an external stylesheet: {href!r}\n"
                "All stylesheets must be local so the demo works offline."
            )


# ---------------------------------------------------------------------------
# index.html — rating and payment values
# ---------------------------------------------------------------------------

def test_index_contains_rating_30_percent() -> None:
    """
    WHY: The demo story is built around a 30% combined rating. If this value
    disappears from the page, the dashboard no longer matches the narrative
    we walk judges through.
    """
    raw_html = INDEX_HTML.read_text(encoding="utf-8")
    assert "30%" in raw_html, (
        "index.html must display the veteran's 30% combined disability rating."
    )


def test_index_contains_monthly_payment() -> None:
    """
    WHY: The $524.31 monthly payment figure is a key demo talking point —
    it shows the financial stakes of the denied claims. Losing it breaks the story.
    """
    raw_html = INDEX_HTML.read_text(encoding="utf-8")
    assert "$524.31" in raw_html, (
        "index.html must display the $524.31 monthly payment amount."
    )


# ---------------------------------------------------------------------------
# index.html — conditions table structure
# ---------------------------------------------------------------------------

def test_index_conditions_table_has_six_rows() -> None:
    """
    WHY: The demo veteran has exactly 6 rated conditions (4 granted, 2 denied).
    The entire appeal narrative depends on this count. If a row is added or
    removed, the "2 of your conditions were denied" callout becomes incorrect.
    """
    raw_html = INDEX_HTML.read_text(encoding="utf-8")

    counter = _TableRowCounter()
    counter.feed(raw_html)

    assert counter.tbody_tr_count == 6, (
        f"index.html conditions table <tbody> must have exactly 6 <tr> rows, "
        f"got {counter.tbody_tr_count}."
    )


def test_index_has_exactly_two_denied_rows() -> None:
    """
    WHY: Exactly 2 conditions are denied (Sleep Apnea and Burn Pit Exposure).
    The denied-row highlight class drives the visual callout that motivates
    the veteran to use VetClaim AI. Wrong count = broken demo story.
    """
    raw_html = INDEX_HTML.read_text(encoding="utf-8")

    counter = _ClassCounter("table-row--denied")
    counter.feed(raw_html)

    assert counter.count == 2, (
        f"index.html must have exactly 2 elements with class 'table-row--denied', "
        f"got {counter.count}."
    )


# ---------------------------------------------------------------------------
# Both pages — US government banner and signed-in user
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("html_path", HTML_FILES)
def test_us_government_banner_present(html_path: Path) -> None:
    """
    WHY: The "An official website of the United States government" banner is a
    hallmark of real VA.gov pages. Its presence makes the mock portal convincing
    to judges and veterans during the demo.
    """
    raw_html = html_path.read_text(encoding="utf-8")

    parser = _TextCollector()
    parser.feed(raw_html)
    page_text = parser.get_text()

    assert "An official website of the United States government" in page_text, (
        f"{html_path.name} must contain the US government banner text."
    )


@pytest.mark.parametrize("html_path", HTML_FILES)
def test_signed_in_as_james_wilson(html_path: Path) -> None:
    """
    WHY: The demo uses a specific fictional veteran — James R. Wilson. Both pages
    must show him as signed in so the session feels consistent throughout the demo
    flow (dashboard → confirmation page).
    """
    raw_html = html_path.read_text(encoding="utf-8")

    parser = _TextCollector()
    parser.feed(raw_html)
    page_text = parser.get_text()

    assert "Signed in as James R. Wilson" in page_text, (
        f"{html_path.name} must show 'Signed in as James R. Wilson' in the nav."
    )


# ---------------------------------------------------------------------------
# style.css — VA design tokens
# ---------------------------------------------------------------------------

def test_css_contains_va_navy() -> None:
    """
    WHY: #112e51 is the VA navy blue used for headers and the rating banner.
    It's the most recognisable VA.gov colour — losing it makes the portal look
    nothing like the real site.
    """
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "#112e51" in css, "style.css must define the VA navy colour #112e51."


def test_css_contains_va_blue() -> None:
    """
    WHY: #005ea2 is the VA link/button blue from the USWDS design system.
    It must be present so interactive elements match VA.gov's visual language.
    """
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "#005ea2" in css, "style.css must define the VA blue #005ea2."


def test_css_contains_va_green() -> None:
    """
    WHY: #2e8540 is the VA success/granted green used for 'Service Connected'
    decisions and the submission notification banner. It signals positive outcomes.
    """
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "#2e8540" in css, "style.css must define the VA green #2e8540."


def test_css_contains_va_red() -> None:
    """
    WHY: #b50909 is the VA error/denied red used for 'Denied' decisions.
    It draws the veteran's eye to the denied rows — the hook for the demo story.
    """
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "#b50909" in css, "style.css must define the VA red #b50909."


def test_css_contains_responsive_breakpoint_900px() -> None:
    """
    WHY: The 900px breakpoint collapses the two-column layout to a single column
    on tablets. Without it, the portal is unusable on smaller screens and fails
    the responsive layout requirement.
    """
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "max-width: 900px" in css, (
        "style.css must contain a @media rule for max-width: 900px "
        "to support the responsive tablet layout."
    )


# ---------------------------------------------------------------------------
# va_api.js — no hardcoded API keys
# ---------------------------------------------------------------------------

def test_va_api_js_no_hardcoded_keys() -> None:
    """
    WHY: API keys must never be hardcoded in JS source — they would be committed
    to git and exposed publicly. The keys are injected via <meta> tags in the HTML
    so they stay out of version control. This test ensures no one accidentally
    pastes a key directly into the JS file.

    The specific key values come from the <meta> tags in index.html:
      - va-api-key:       ZLUUzRYuYpPjxUPTyhunsA7Ott172cq2
      - va-forms-api-key: VgKI6h0JCbHe2f9eZwgxKmia9R5HKNfH
    """
    js_source = VA_API_JS.read_text(encoding="utf-8")

    # These are the actual sandbox key values from the index.html meta tags.
    # If either appears literally in the JS, the key has been hardcoded.
    hardcoded_keys = [
        "ZLUUzRYuYpPjxUPTyhunsA7Ott172cq2",
        "VgKI6h0JCbHe2f9eZwgxKmia9R5HKNfH",
    ]

    for key in hardcoded_keys:
        assert key not in js_source, (
            f"va_api.js must NOT contain the hardcoded API key {key!r}. "
            "Keys must be read from <meta> tags at runtime, not embedded in source."
        )
