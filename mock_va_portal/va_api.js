/**
 * va_api.js — Mock VA Portal Frontend Logic
 *
 * Two responsibilities:
 * 1. Fetch the veteran's service branch from the real VA Benefits Reference
 *    Data API and show a "✓ VA Verified" badge (proves live VA connectivity)
 * 2. Poll the mock VA portal server for new appeal submissions from VetClaim AI
 *    and show a notification banner on the dashboard when one arrives
 *
 * The mock VA portal server runs at http://localhost:5050 (server.py).
 * The real VA sandbox API runs at https://sandbox-api.va.gov.
 */

const VA_SANDBOX_BASE  = "https://sandbox-api.va.gov/services/benefits-reference-data/v1";
const VA_PORTAL_BASE   = "http://localhost:5050";

// Read the API key from the <meta> tag so it's not hardcoded in JS source.
// In production this would be injected server-side.
const VA_API_KEY = document.querySelector('meta[name="va-api-key"]')?.content || "";

// Default branch code — overridden per-profile when the switcher is used
const DEMO_VETERAN_BRANCH_CODE = "ARMY";

// How often (ms) to poll the portal server for new submissions.
// 3 seconds is fast enough to feel live without hammering the server.
const POLL_INTERVAL_MS = 3000;


/* ── 1. VA Benefits Reference Data API ─────────────────────────── */

/**
 * Fetch service branches from the real VA API and update the Branch field
 * with the official VA description + a "✓ VA Verified" badge.
 * Falls back gracefully if the API is unreachable during the demo.
 */
async function initVABranchVerification() {
  initVABranchVerificationForProfile(DEMO_VETERAN_BRANCH_CODE);
}

/**
 * Same as initVABranchVerification but accepts a branch code so it works
 * for any profile, not just the default James Wilson / ARMY profile.
 *
 * @param {string} branchCode - e.g. "ARMY", "NAVY", "MARINES"
 */
async function initVABranchVerificationForProfile(branchCode) {
  const branchEl = document.getElementById("va-service-branch");
  if (!branchEl) return;

  branchEl.textContent = "Loading...";

  // Remove any existing badge before adding a new one
  const existingBadge = branchEl.parentNode.querySelector(".va-verified-badge");
  if (existingBadge) existingBadge.remove();

  try {
    const response = await fetch(`${VA_SANDBOX_BASE}/service-branches`, {
      headers: { "apiKey": VA_API_KEY }
    });

    if (!response.ok) throw new Error(`VA API ${response.status}`);

    const data = await response.json();
    const match = data.items.find(b => b.code === branchCode);
    branchEl.textContent = match ? match.description : branchCode;

    // Add the verified badge — visual proof of live VA API connection
    const badge = document.createElement("span");
    badge.className = "va-verified-badge";
    badge.title = "Verified against VA Benefits Reference Data API";
    badge.textContent = "✓ VA Verified";
    branchEl.parentNode.appendChild(badge);

  } catch (err) {
    // API unreachable — fall back silently so the demo isn't blocked
    console.warn("VA API unavailable, using fallback:", err.message);
    branchEl.textContent = branchCode;
  }
}


/* ── 2. Submission polling ──────────────────────────────────────── */

/**
 * Poll the mock VA portal server every 3 seconds for new submissions.
 * When a submission arrives from VetClaim AI, show a notification banner
 * and populate the Filed Appeals table on the dashboard.
 */
function startSubmissionPolling() {
  const notificationArea = document.getElementById("submission-notification");
  if (!notificationArea) return;

  const seenIds = new Set();

  async function poll() {
    try {
      const response = await fetch(`${VA_PORTAL_BASE}/submissions`);
      if (!response.ok) return;

      const submissions = await response.json();

      // Refresh the full appeals table on every poll cycle
      refreshAppealsTable(submissions);

      // Show banner only for the newest submission we haven't announced yet
      const newSubmission = submissions.find(s => !seenIds.has(s.id));
      if (!newSubmission) return;

      seenIds.add(newSubmission.id);
      showSubmissionBanner(newSubmission);

    } catch (err) {
      // Server not running — expected before demo starts
    }
  }

  setInterval(poll, POLL_INTERVAL_MS);
  poll();
}

/**
 * Refresh the Filed Appeals table with all current submissions.
 */
function refreshAppealsTable(submissions) {
  const section = document.getElementById("pending-appeals-section");
  const tbody   = document.getElementById("appeals-tbody");
  const badge   = document.getElementById("appeals-count");
  if (!section || !tbody) return;

  if (submissions.length === 0) {
    section.style.display = "none";
    return;
  }

  section.style.display = "block";
  if (badge) badge.textContent = submissions.length;

  tbody.innerHTML = submissions.map(s => `
    <tr class="appeals-row">
      <td><code class="conf-code">${s.confirmation_number}</code></td>
      <td>${s.veteran_name}</td>
      <td class="conditions-cell">${s.conditions}</td>
      <td class="date-cell">${s.submitted_at}</td>
      <td>
        <a href="confirmation.html?id=${s.id}" class="va-btn va-btn--primary va-btn--sm">
          View →
        </a>
      </td>
    </tr>
  `).join("");
}

/**
 * Inject a green notification banner when a new submission is detected.
 */
function showSubmissionBanner(submission) {
  const notificationArea = document.getElementById("submission-notification");
  if (!notificationArea) return;

  notificationArea.innerHTML = `
    <div class="submission-banner">
      <div class="submission-banner__icon">📬</div>
      <div class="submission-banner__text">
        <strong>New appeal documents received from VetClaim AI.</strong>
        Confirmation: <code>${submission.confirmation_number}</code>
        &nbsp;&bull;&nbsp; ${submission.submitted_at}
      </div>
      <a href="confirmation.html?id=${submission.id}" class="va-btn va-btn--primary submission-banner__btn">
        View Submission →
      </a>
    </div>
  `;
}


/* ── Download All Documents ─────────────────────────────────── */

/**
 * Fetch all claim documents for the active profile and download them as a
 * zip file containing individual PDFs inside a folder named after the veteran.
 *
 * @param {object} profile - the active PROFILES entry from profiles.js
 */
async function downloadAllDocuments(profile) {
  const btn = document.getElementById("download-all-docs");
  if (!btn) return;

  const originalText = btn.textContent;
  btn.textContent = "⏳ Preparing download…";
  btn.disabled = true;

  try {
    const zip = new JSZip();
    // Folder name: e.g. "James_T_Milner"
    const folderName = profile.name.replace(/\s+/g, "_");
    const folder = zip.folder(folderName);

    for (const doc of profile.documents) {
      if (!doc.url || doc.url === "#") continue;
      const url = doc.url.startsWith("http") ? doc.url : `${VA_PORTAL_BASE}${doc.url}`;
      try {
        const res = await fetch(url);
        if (!res.ok) continue;
        const bytes = await res.arrayBuffer();
        // Use the original filename from the URL
        const filename = doc.url.split("/").pop();
        folder.file(filename, bytes);
      } catch (e) {
        console.warn(`Skipping ${doc.name}:`, e.message);
      }
    }

    const blob = await zip.generateAsync({ type: "blob" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${folderName}_Claim_Documents.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(a.href), 10000);

  } catch (err) {
    console.error("Download failed:", err);
    alert("Could not generate the zip. Make sure the portal server is running.");
  } finally {
    btn.textContent = originalText;
    btn.disabled = false;
  }
}




document.addEventListener("DOMContentLoaded", () => {
  initProfileSwitcher();   // build the nav dropdown before anything else
  renderProfile(activeProfileKey);  // wire up the download button and render default profile
  initVABranchVerification();
  startSubmissionPolling();
});
