import { useState } from 'react'

const NAV_BLUE = '#1B3A6B'

const FLAG_CONFIG = {
  UNDER_RATED:            { label: 'Under-Rated',            bg: '#FEF3C7', border: '#D97706', text: '#92400E' },
  WRONG_CODE:             { label: 'Wrong Code',             bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  MISSING_NEXUS:          { label: 'Missing Nexus',          bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  PACT_ACT_ELIGIBLE:      { label: 'PACT Act Eligible',      bg: '#D1FAE5', border: '#059669', text: '#064E3B' },
  TDIU_ELIGIBLE:          { label: 'TDIU Eligible',          bg: '#DBEAFE', border: '#2563EB', text: '#1E3A8A' },
  COMBINED_RATING_ERROR:  { label: 'Rating Math Error',      bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  SEPARATE_RATING_MISSED: { label: 'Separate Rating Missed', bg: '#FEF9C3', border: '#CA8A04', text: '#713F12' },
}

function FlagBadge({ flagType }) {
  const cfg = FLAG_CONFIG[flagType] || { label: flagType, bg: '#F3F4F6', border: '#9CA3AF', text: '#374151' }
  return (
    <span
      className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full border"
      style={{ background: cfg.bg, borderColor: cfg.border, color: cfg.text }}
    >
      {cfg.label}
    </span>
  )
}

function StatCard({ label, value, highlight }) {
  return (
    <div
      className="rounded-xl p-4 border"
      style={highlight
        ? { background: '#EFF6FF', borderColor: '#BFDBFE' }
        : { background: '#F9FAFB', borderColor: '#E5E7EB' }}
    >
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p
        className="text-xl font-bold"
        style={{ color: highlight ? NAV_BLUE : '#111827' }}
      >
        {value}
      </p>
    </div>
  )
}

function fmtUSD(v) {
  if (v == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
}

export default function AuditResultsPage({ result, jobId, onBack, onCallClick }) {
  const [submitState, setSubmitState] = useState('idle') // idle | submitting | success | error
  const [confirmation, setConfirmation] = useState(null)

  const auditResult   = result?.audit_result ?? {}
  const flags         = auditResult.flags ?? []
  const vaFormLinks   = result?.va_form_links ?? []
  const missingNexus  = flags.filter(f => f.flag_type === 'MISSING_NEXUS')
  const otherFlags    = flags.filter(f => f.flag_type !== 'MISSING_NEXUS')

  async function handleSubmitAppeal() {
    setSubmitState('submitting')
    try {
      const res = await fetch('/api/submit-appeal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      })
      const body = await res.json()
      if (res.ok) { setConfirmation(body.confirmation_number); setSubmitState('success') }
      else setSubmitState('error')
    } catch { setSubmitState('error') }
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Nav */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7"/>
              </svg>
              Back
            </button>
            <span className="text-gray-300">|</span>
            <span className="font-bold text-base" style={{ color: NAV_BLUE }}>VetClaim AI</span>
          </div>
          <span
            className="text-xs font-semibold px-3 py-1 rounded-full"
            style={{ background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0' }}
          >
            Audit Complete
          </span>
        </div>
      </nav>

      <main className="flex-1 max-w-3xl mx-auto w-full px-6 py-10 space-y-6">

        {/* ── Veteran header ── */}
        <div className="fade-in-up rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between flex-wrap gap-3 mb-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-0.5">Veteran</p>
              <h1 className="text-2xl font-bold text-gray-900">
                {auditResult.veteran_name || 'Unknown Veteran'}
              </h1>
            </div>
            <span
              className="text-xs font-semibold px-3 py-1 rounded-full border"
              style={{ background: '#DBEAFE', borderColor: '#93C5FD', color: NAV_BLUE }}
            >
              {flags.length} Finding{flags.length !== 1 ? 's' : ''} Detected
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <StatCard label="Current Rating"        value={`${auditResult.current_combined_rating ?? '—'}%`} />
            <StatCard label="Corrected Rating"      value={`${auditResult.corrected_combined_rating ?? '—'}%`} highlight />
            <StatCard label="Current Monthly Pay"   value={fmtUSD(auditResult.current_monthly_pay_usd)} />
            <StatCard label="Potential Monthly Pay" value={fmtUSD(auditResult.potential_monthly_pay_usd)} highlight />
            <StatCard label="Annual Impact"         value={fmtUSD(auditResult.annual_impact_usd)} highlight />
          </div>
        </div>

        {/* ── Audit flags ── */}
        {otherFlags.length > 0 && (
          <div className="fade-in-up-2 rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-bold text-gray-900 mb-4">🚩 Audit Findings</h2>
            <div className="space-y-3">
              {otherFlags.map((flag, i) => (
                <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                  <div className="flex items-start justify-between gap-3 flex-wrap mb-2">
                    <p className="font-semibold text-sm text-gray-900">{flag.condition_name}</p>
                    <FlagBadge flagType={flag.flag_type} />
                  </div>
                  <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs mb-2">
                    {flag.assigned_rating != null && (
                      <span className="text-gray-500">Assigned: <strong className="text-gray-800">{flag.assigned_rating}%</strong></span>
                    )}
                    {flag.eligible_rating != null && (
                      <span className="text-gray-500">Eligible: <strong style={{ color: NAV_BLUE }}>{flag.eligible_rating}%</strong></span>
                    )}
                    {flag.cfr_citation && (
                      <span className="text-gray-500">CFR: <strong className="text-gray-800">{flag.cfr_citation}</strong></span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 leading-relaxed mb-2">{flag.explanation}</p>
                  {flag.confidence != null && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Confidence</span>
                      <div className="flex-1 max-w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${Math.round(flag.confidence * 100)}%`, background: NAV_BLUE }}
                        />
                      </div>
                      <span className="text-xs font-semibold" style={{ color: NAV_BLUE }}>
                        {Math.round(flag.confidence * 100)}%
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Rejection reasons ── */}
        {missingNexus.length > 0 && (
          <div className="fade-in-up-2 rounded-xl border border-red-200 p-6">
            <h2 className="text-base font-bold text-gray-900 mb-4">❌ Denial Reasons</h2>
            <div className="space-y-3">
              {missingNexus.map((flag, i) => (
                <div key={i} className="rounded-lg border border-red-100 bg-red-50 p-4">
                  <p className="font-semibold text-sm text-red-800 mb-1">{flag.condition_name}</p>
                  <p className="text-xs text-red-700 leading-relaxed">{flag.explanation}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Filled VA forms ── */}
        {vaFormLinks.length > 0 && (
          <div className="fade-in-up-3 rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-bold text-gray-900 mb-4">📄 Pre-Filled VA Forms</h2>
            <div className="space-y-2">
              {vaFormLinks.map((form, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                  <div>
                    <p className="font-semibold text-sm text-gray-900">VA Form {form.form_number}</p>
                    {form.fields_filled != null && (
                      <p className="text-xs text-gray-400 mt-0.5">{form.fields_filled} of {form.fields_found} fields filled</p>
                    )}
                  </div>
                  <a
                    href={`/api/download?path=${encodeURIComponent(form.filled_path)}`}
                    download
                    className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg text-white transition-colors"
                    style={{ background: NAV_BLUE }}
                    onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
                    onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
                  >
                    ⬇ Download
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Submit Appeal to VA ── */}
        {vaFormLinks.length > 0 && (
          <div className="fade-in-up-3 rounded-xl border p-6" style={{ borderColor: '#93C5FD', background: '#F0F7FF' }}>
            <h2 className="text-base font-bold text-gray-900 mb-1">🏛️ Submit Appeal to VA Portal</h2>
            <p className="text-xs text-gray-500 mb-5">
              Send your pre-filled forms directly to the VA eBenefits portal. They will appear on your
              dashboard instantly.
            </p>

            {submitState === 'success' ? (
              <div className="text-center py-2">
                <p className="text-green-700 font-bold text-sm mb-1">✅ Appeal Submitted!</p>
                <p className="text-gray-500 text-xs mb-3">
                  Confirmation: <span className="font-mono font-bold" style={{ color: NAV_BLUE }}>{confirmation}</span>
                </p>
                <a
                  href="http://localhost:5050"
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs underline font-semibold"
                  style={{ color: NAV_BLUE }}
                >
                  View on VA Portal →
                </a>
              </div>
            ) : submitState === 'error' ? (
              <div className="text-center">
                <p className="text-red-600 text-sm font-semibold mb-2">Submission failed — is the VA portal running?</p>
                <button
                  onClick={handleSubmitAppeal}
                  className="px-6 py-2 rounded-lg text-sm font-semibold text-white"
                  style={{ background: NAV_BLUE }}
                >
                  Retry
                </button>
              </div>
            ) : (
              <button
                onClick={handleSubmitAppeal}
                disabled={submitState === 'submitting'}
                className="w-full py-3 rounded-lg font-semibold text-sm text-white flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                style={{ background: NAV_BLUE }}
                onMouseEnter={e => { if (submitState !== 'submitting') e.currentTarget.style.background = '#0F2444' }}
                onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
              >
                {submitState === 'submitting' ? (
                  <>
                    <svg className="w-4 h-4 spin-cw" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Submitting to VA Portal…
                  </>
                ) : '🏛️ Submit Appeal'}
              </button>
            )}
          </div>
        )}

        {/* ── Call the VA ── */}
        <div className="fade-in-up-4 rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-bold text-gray-900 mb-1">Call the VA</h2>
          <p className="text-gray-500 text-xs mb-4">
            Our AI agent calls your phone, reads a consent disclosure, then connects to
            1-800-827-1000 and requests a status update on your behalf.
          </p>
          <button
            onClick={onCallClick}
            className="w-full py-2.5 rounded-lg font-semibold text-sm text-white flex items-center justify-center gap-2"
            style={{ background: NAV_BLUE }}
            onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
            onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
            </svg>
            Open VA Calling Agent
          </button>
        </div>

        {/* ── AI Notes ── */}
        {auditResult.auditor_notes && (
          <div className="fade-in-up-4 rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-bold text-gray-900 mb-3">🤖 AI Reasoning</h2>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">{auditResult.auditor_notes}</p>
          </div>
        )}

        {/* ── Rule-based report ── */}
        {result?.rule_based_triggered && result?.rule_based_report && (
          <div className="rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-bold text-gray-900 mb-3">📋 Rule-Based Report</h2>
            <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-wrap">{result.rule_based_report}</p>
          </div>
        )}

        <div className="pb-10 text-center">
          <button
            onClick={onBack}
            className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            ← Start a New Claim
          </button>
        </div>
      </main>
    </div>
  )
}
