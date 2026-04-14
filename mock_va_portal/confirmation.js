/**
 * confirmation.js — Confirmation Page Logic
 *
 * Reads the submission ID from the URL query string (?id=VA-2026-NOD-XXXXXX),
 * fetches the submission metadata from the mock VA portal server,
 * renders the confirmation details, and embeds the PDF inline via an <iframe>.
 *
 * If no ID is in the URL, shows the most recent submission instead —
 * this lets the presenter navigate directly to confirmation.html without
 * needing to click through from the dashboard notification.
 */

const VA_PORTAL_BASE   = "http://localhost:5050";
const VA_FORMS_API_BASE = "https://sandbox-api.va.gov/services/va_forms/v0";

// Read the Forms API key from the <meta> tag
const VA_FORMS_API_KEY = document.querySelector('meta[name="va-forms-api-key"]')?.content || "";

/**
 * Get the submission ID from the URL query string.
 * e.g. confirmation.html?id=VA-2026-NOD-048821 → "VA-2026-NOD-048821"
 * Returns null if no id param is present.
 */
function getSubmissionIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

/**
 * Fetch a specific submission by ID, or the most recent one if no ID given.
 * Returns the submission object or null if nothing is found.
 */
async function fetchSubmission(submissionId) {
  const response = await fetch(`${VA_PORTAL_BASE}/submissions`);
  if (!response.ok) throw new Error(`Server returned ${response.status}`);

  const submissions = await response.json();
  if (submissions.length === 0) return null;

  if (submissionId) {
    return submissions.find(s => s.id === submissionId) || null;
  }

  // No ID specified — show the most recent submission (first in the reversed list)
  return submissions[0];
}

/**
 * Fetch live form details from the VA Forms API for a given form number.
 * Used to show a "✓ VA Verified" badge next to submitted documents.
 * Falls back gracefully if the API is unreachable.
 *
 * @param {string} formId - e.g. "20-0996", "20-0995", "21-526EZ", "21-8940"
 */
async function fetchVAFormDetails(formId) {
  if (!formId) return null;
  try {
    const response = await fetch(
      `${VA_FORMS_API_BASE}/forms?query=${encodeURIComponent(formId)}`,
      { headers: { "apiKey": VA_FORMS_API_KEY } }
    );
    if (!response.ok) throw new Error(`VA Forms API ${response.status}`);

    const data = await response.json();
    // Find the form whose form_name matches our target (e.g. "VA20-0996")
    const match = data.data?.find(f =>
      f.attributes?.form_name?.replace(/\s/g, "").includes(formId.replace(/-/g, ""))
    ) || data.data?.[0];

    const form = match?.attributes;
    if (!form) throw new Error(`Form ${formId} not found in VA API response`);

    return {
      name: form.form_name,
      title: form.title,
      lastRevised: form.last_revision_on,
      pages: form.pages,
      officialUrl: form.url,
      detailsUrl: form.form_details_url,
    };
  } catch (err) {
    console.warn(`VA Forms API unavailable for ${formId}:`, err.message);
    return null;
  }
}

/**
 * Build a small "✓ VA Verified" form badge HTML string from the form details.
 * Shown in the documents table next to the NOD row.
 */
function buildFormBadge(formDetails) {
  if (!formDetails) return "";
  return `
    <span class="va-form-badge">
      ✓ VA Verified &nbsp;·&nbsp;
      <a href="${formDetails.officialUrl}" target="_blank">${formDetails.name}</a>
      &nbsp;·&nbsp; Last revised ${formDetails.lastRevised}
    </span>
  `;
}

/**
 * Build and inject the full confirmation page HTML from a submission object.
 * Keeps the HTML in JS here so confirmation.html stays clean and the
 * data is always live from the server.
 */
async function renderConfirmation(submission) {
  const pdfUrl = `${VA_PORTAL_BASE}/submissions/${submission.id}/pdf`;

  // Fetch VA API verification badges for all docs that have a va_form_id, in parallel
  const formDetailsList = await Promise.all(
    submission.documents.map(doc =>
      doc.va_form_id ? fetchVAFormDetails(doc.va_form_id) : Promise.resolve(null)
    )
  );

  // Build the documents table rows with per-row VA Verified badges
  const docRows = submission.documents.map((doc, index) => {
    const badge = buildFormBadge(formDetailsList[index]);
    return `
      <tr>
        <td>
          <strong>${doc.name}</strong><br />
          <span class="doc-subtitle">${doc.form}</span>
          ${badge}
        </td>
        <td class="decision-granted">✓ Received</td>
        <td>${doc.pages}</td>
      </tr>
    `;
  }).join("");

  // Build the conditions list from the comma-separated conditions string
  const conditionItems = submission.conditions.split(",").map(c => `
    <li><span class="confirm-condition-code">${c.trim()}</span></li>
  `).join("");

  document.getElementById("confirmation-content").innerHTML = `

    <!-- Success banner -->
    <div class="confirm-success-banner">
      <div class="confirm-success-banner__icon">✅</div>
      <div class="confirm-success-banner__text">
        <h1>Your appeal documents have been received by the VA.</h1>
        <p>VetClaim AI submitted your Notice of Disagreement and supporting evidence on your behalf.</p>
      </div>
    </div>

    <!-- Confirmation number — the headline proof point -->
    <div class="confirm-report-card">
      <div class="confirm-report-card__label">VA Confirmation Number</div>
      <div class="confirm-report-card__number">${submission.confirmation_number}</div>
      <div class="confirm-report-card__meta">
        Submitted: ${submission.submitted_at}
        &nbsp;&bull;&nbsp;
        Submitted by: <strong>VetClaim AI</strong> on behalf of ${submission.veteran_name}
      </div>
    </div>

    <!-- Two-column layout -->
    <div class="va-content-grid">

      <section class="va-card">
        <h2>Documents Received</h2>
        <table class="va-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Status</th>
              <th>Pages</th>
            </tr>
          </thead>
          <tbody>${docRows}</tbody>
        </table>

        <h3 style="margin-top:24px; margin-bottom:12px; font-size:16px; color:#112e51;">
          Conditions Under Appeal
        </h3>
        <ul class="confirm-conditions-list">${conditionItems}</ul>

        <!-- PDF embedded inline — the actual document VetClaim AI submitted -->
        <h3 style="margin-top:24px; margin-bottom:12px; font-size:16px; color:#112e51;">
          Submitted Document
        </h3>
        <iframe
          src="${pdfUrl}"
          class="confirm-pdf-viewer"
          title="Notice of Disagreement — submitted by VetClaim AI"
        >
          <p>Your browser cannot display PDFs inline.
             <a href="${pdfUrl}" target="_blank">Open the PDF</a>
          </p>
        </iframe>
      </section>

      <aside class="va-sidebar">

        <div class="va-card va-card--compact">
          <h3>What Happens Next</h3>
          <ol class="confirm-steps-list">
            <li>
              <strong>Acknowledgment letter</strong>
              <span>Within 5 business days — VA confirms receipt and assigns a docket number</span>
            </li>
            <li>
              <strong>Assigned to VA reviewer</strong>
              <span>Your NOD will be assigned to a Decision Review Officer (DRO)</span>
            </li>
            <li>
              <strong>Evidence review period</strong>
              <span>90-day window to submit additional evidence if needed</span>
            </li>
            <li>
              <strong>Decision issued</strong>
              <span>Estimated 4–6 months — you will be notified by mail and on VA.gov</span>
            </li>
          </ol>
        </div>

        <div class="va-card va-card--compact">
          <h3>Save Your Confirmation</h3>
          <p style="font-size:14px; margin-bottom:12px;">
            Reference this number in all future correspondence with the VA.
          </p>
          <div class="confirm-save-number">${submission.confirmation_number}</div>
          <a href="${pdfUrl}" target="_blank" class="va-btn va-btn--outline"
             style="margin-top:12px; display:inline-block;">
            📄 Download Appeal PDF
          </a>
        </div>

        <div class="va-card va-card--compact">
          <h3>Track Your Appeal</h3>
          <p style="font-size:14px; margin-bottom:12px;">
            Check the status of your appeal at any time on VA.gov.
          </p>
          <a href="#" class="va-btn va-btn--outline">View Appeal Status →</a>
        </div>

      </aside>
    </div>

    <div style="margin-bottom:32px;">
      <a href="index.html" class="va-btn va-btn--outline">← Return to My Benefits</a>
    </div>
  `;
}

/**
 * Show an error state if the submission can't be loaded.
 * Gives the presenter a clear message instead of a blank page.
 */
function renderError(message) {
  document.getElementById("confirmation-content").innerHTML = `
    <div class="va-card" style="text-align:center; padding:48px;">
      <h2 style="color:#b50909;">Unable to load submission</h2>
      <p style="color:#71767a; margin-top:8px;">${message}</p>
      <a href="index.html" class="va-btn va-btn--outline" style="margin-top:24px; display:inline-block;">
        ← Return to My Benefits
      </a>
    </div>
  `;
}

/**
 * Main: load and render the confirmation page on DOM ready.
 */
async function init() {
  const submissionId = getSubmissionIdFromUrl();

  try {
    const submission = await fetchSubmission(submissionId);

    if (!submission) {
      renderError("No submissions found. Make sure the VetClaim AI app has submitted an appeal and the portal server is running.");
      return;
    }

    await renderConfirmation(submission);

  } catch (err) {
    renderError(`Could not connect to the VA portal server at ${VA_PORTAL_BASE}. Make sure server.py is running.`);
  }
}

document.addEventListener("DOMContentLoaded", init);
