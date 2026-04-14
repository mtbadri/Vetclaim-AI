import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  Home, AlertTriangle, FileText, Phone, MessageSquare,
  ChevronDown, Download, Send, RefreshCw, Loader2,
} from 'lucide-react'

const NAV_BLUE = '#1B3A6B'
const GOLD     = '#9B7E2A'

const FLAG_CONFIG = {
  UNDER_RATED:            { label: 'Under-Rated',            bg: '#FEF3C7', border: '#D97706', text: '#92400E' },
  WRONG_CODE:             { label: 'Wrong Code',             bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  MISSING_NEXUS:          { label: 'Missing Nexus',          bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  PACT_ACT_ELIGIBLE:      { label: 'PACT Act Eligible',      bg: '#D1FAE5', border: '#059669', text: '#064E3B' },
  TDIU_ELIGIBLE:          { label: 'TDIU Eligible',          bg: '#DBEAFE', border: '#2563EB', text: '#1E3A8A' },
  COMBINED_RATING_ERROR:  { label: 'Rating Math Error',      bg: '#FEE2E2', border: '#DC2626', text: '#7F1D1D' },
  SEPARATE_RATING_MISSED: { label: 'Separate Rating Missed', bg: '#FEF9C3', border: '#CA8A04', text: '#713F12' },
}

const NAV_ITEMS = [
  { id: 'overview',  label: 'Overview',  Icon: Home },
  { id: 'findings',  label: 'Findings',  Icon: AlertTriangle },
  { id: 'forms',     label: 'Forms',     Icon: FileText },
  { id: 'vacall',    label: 'VA Call',   Icon: Phone },
  { id: 'chat',      label: 'Chat',      Icon: MessageSquare },
]

function fmtUSD(v) {
  if (v == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v)
}

function FlagBadge({ flagType }) {
  const cfg = FLAG_CONFIG[flagType] || { label: flagType, bg: '#F3F4F6', border: '#9CA3AF', text: '#374151' }
  return (
    <span className="inline-block text-xs font-semibold px-2.5 py-0.5 rounded-full border"
      style={{ background: cfg.bg, borderColor: cfg.border, color: cfg.text }}>
      {cfg.label}
    </span>
  )
}

function SectionLabel({ children }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: NAV_BLUE }}>
      {children}
    </p>
  )
}

// ─────────────────────────────────────────────
// OVERVIEW
// ─────────────────────────────────────────────
function OverviewSection({ audit, result }) {
  const stats = [
    { label: 'Current Rating',        value: `${audit.current_combined_rating ?? '—'}%`,   highlight: false },
    { label: 'Corrected Rating',      value: `${audit.corrected_combined_rating ?? '—'}%`, highlight: true  },
    { label: 'Current Monthly Pay',   value: fmtUSD(audit.current_monthly_pay_usd),         highlight: false },
    { label: 'Potential Monthly Pay', value: fmtUSD(audit.potential_monthly_pay_usd),       highlight: true  },
    { label: 'Annual Impact',         value: fmtUSD(audit.annual_impact_usd),               highlight: true  },
    { label: 'TDIU Eligible',         value: audit.tdiu_eligible === true ? 'Yes' : audit.tdiu_eligible === false ? 'No' : '—', highlight: false },
  ]

  return (
    <div className="space-y-8 fade-in-up">
      {/* Veteran header */}
      <div>
        <SectionLabel>Veteran Overview</SectionLabel>
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
          {audit.veteran_name || 'Unknown Veteran'}
        </h2>
        <p className="text-gray-500 text-sm leading-relaxed mt-1">
          AI-generated audit of your VA disability claim documents.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {stats.map(({ label, value, highlight }) => (
          <div key={label} className="rounded-xl border p-5"
            style={highlight
              ? { background: '#EEF2FF', borderColor: '#C7D2FE' }
              : { background: '#fff', borderColor: '#E5E7EB' }}>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">{label}</p>
            <p className="text-xl font-bold" style={{ color: highlight ? NAV_BLUE : '#111827' }}>{value}</p>
          </div>
        ))}
      </div>

      {/* AI Reasoning */}
      {audit.auditor_notes && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <SectionLabel>AI Reasoning</SectionLabel>
          <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap mt-1">{audit.auditor_notes}</p>
        </div>
      )}

      {/* Rule-Based Report */}
      {result?.rule_based_triggered && result?.rule_based_report && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <SectionLabel>Rule-Based Report</SectionLabel>
          <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap mt-1">{result.rule_based_report}</p>
        </div>
      )}

      {/* Disclaimer */}
      <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <svg className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-0.5">Please Note</p>
          <p className="text-xs text-amber-700 leading-relaxed">
            AI can make mistakes. Always verify your claim status directly with the VA or a qualified VSO before taking action.
          </p>
        </div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// FINDINGS
// ─────────────────────────────────────────────
function FindingsSection({ flags }) {
  const denial = flags.filter(f => f.flag_type === 'MISSING_NEXUS')
  const others = flags.filter(f => f.flag_type !== 'MISSING_NEXUS')

  return (
    <div className="space-y-8 fade-in-up">
      <div>
        <SectionLabel>Audit Results</SectionLabel>
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">Findings</h2>
        <p className="text-gray-500 text-sm leading-relaxed mt-1">
          {flags.length} issue{flags.length !== 1 ? 's' : ''} identified in your claim documents.
        </p>
      </div>

      {others.length > 0 && (
        <div className="space-y-3">
          {others.map((flag, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between gap-3 flex-wrap mb-3">
                <p className="font-semibold text-sm text-gray-900">{flag.condition_name}</p>
                <FlagBadge flagType={flag.flag_type} />
              </div>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs mb-3">
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
              <p className="text-xs text-gray-600 leading-relaxed mb-3">{flag.explanation}</p>
              {flag.confidence != null && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">Confidence</span>
                  <div className="flex-1 max-w-24 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${Math.round(flag.confidence * 100)}%`, background: NAV_BLUE }} />
                  </div>
                  <span className="text-xs font-semibold" style={{ color: NAV_BLUE }}>{Math.round(flag.confidence * 100)}%</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {denial.length > 0 && (
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <SectionLabel>Denial Reasons</SectionLabel>
          <div className="space-y-3 mt-3">
            {denial.map((flag, i) => (
              <div key={i} className="rounded-lg border border-red-100 bg-red-50 p-4">
                <p className="font-semibold text-sm text-red-800 mb-1">{flag.condition_name}</p>
                <p className="text-xs text-red-700 leading-relaxed">{flag.explanation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {flags.length === 0 && (
        <p className="text-sm text-gray-400 text-center py-12">No findings detected.</p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// FORMS
// ─────────────────────────────────────────────
function FormsSection({ vaFormLinks, jobId }) {
  const [submitState, setSubmitState] = useState('idle')
  const [confirmation, setConfirmation] = useState(null)

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

  if (!vaFormLinks || vaFormLinks.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-12">No pre-filled forms available.</p>
  }

  return (
    <div className="space-y-8 fade-in-up">
      <div>
        <SectionLabel>Pre-Filled Documents</SectionLabel>
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">VA Forms</h2>
        <p className="text-gray-500 text-sm leading-relaxed mt-1">
          Download your completed forms or submit them directly to the VA portal.
        </p>
      </div>

      <div className="space-y-3">
        {vaFormLinks.map((form, i) => (
          <div key={i} className="bg-white rounded-xl border border-gray-200 px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: '#EEF2FF' }}>
                <FileText className="w-5 h-5" style={{ color: NAV_BLUE }} />
              </div>
              <div>
                <p className="font-semibold text-sm text-gray-900">VA Form {form.form_number}</p>
                {form.fields_filled != null && (
                  <p className="text-xs text-gray-400 mt-0.5">{form.fields_filled} of {form.fields_found} fields filled</p>
                )}
              </div>
            </div>
            <a
              href={`/api/download?path=${encodeURIComponent(form.filled_path)}`}
              download
              className="flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg text-white transition-colors"
              style={{ background: NAV_BLUE }}
              onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
              onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </a>
          </div>
        ))}
      </div>

      {/* Submit to VA */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <SectionLabel>VA Portal</SectionLabel>
        <h3 className="text-base font-bold text-gray-900 mt-1 mb-1">Submit Appeal to VA Portal</h3>
        <p className="text-sm text-gray-500 mb-6 leading-relaxed">
          Send your pre-filled forms directly to the VA eBenefits portal. They will appear on your dashboard instantly.
        </p>

        {submitState === 'success' ? (
          <div className="text-center py-2">
            <div className="w-12 h-12 rounded-full bg-green-50 border border-green-200 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
              </svg>
            </div>
            <p className="text-green-700 font-bold text-sm mb-1">Appeal Submitted!</p>
            <p className="text-gray-500 text-xs mb-4">
              Confirmation: <span className="font-mono font-bold" style={{ color: NAV_BLUE }}>{confirmation}</span>
            </p>
            <a href="http://localhost:5050" target="_blank" rel="noreferrer"
              className="text-xs font-semibold underline" style={{ color: NAV_BLUE }}>
              View on VA Portal →
            </a>
          </div>
        ) : submitState === 'error' ? (
          <div className="text-center">
            <p className="text-red-600 text-sm font-semibold mb-3">Submission failed — is the VA portal running?</p>
            <button onClick={handleSubmitAppeal}
              className="px-6 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors"
              style={{ background: NAV_BLUE }}
              onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
              onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}>
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
            {submitState === 'submitting'
              ? <><Loader2 className="w-4 h-4 animate-spin" /> Submitting…</>
              : 'Submit Appeal to VA Portal'}
          </button>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// VA CALL
// ─────────────────────────────────────────────
function normalizePhone(raw) {
  const digits = raw.replace(/\D/g, '')
  if (digits.length === 10) return `+1${digits}`
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`
  return null
}

function VACallSection() {
  const [status, setStatus] = useState('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [callData, setCallData] = useState(null)
  const [fetchingTranscript, setFetchingTranscript] = useState(false)
  const [callInitiated, setCallInitiated] = useState(false)
  const [transcriptOpen, setTranscriptOpen] = useState(false)
  const [phoneInput, setPhoneInput] = useState('')

  const e164 = normalizePhone(phoneInput)

  const handleCall = async () => {
    if (!e164) return
    setStatus('loading')
    setErrorMsg('')
    setCallData(null)
    try {
      const res = await fetch('/api/call-va', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: e164 }),
      })
      const data = await res.json()
      if (!res.ok || data.status === 'error') throw new Error(data.message || data.error || 'Failed to start call')
      setStatus('success')
      setCallInitiated(true)
    } catch (err) {
      setErrorMsg(err.message)
      setStatus('error')
      setCallInitiated(true)
    }
  }

  const fetchTranscript = async () => {
    setFetchingTranscript(true)
    try {
      const res = await fetch('/api/get-transcript')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to fetch transcript')
      setCallData({
        summary: data.summary || '',
        transcript: data.transcript || 'No transcript available yet.',
        duration_seconds: data.duration_seconds,
        ended_reason: data.ended_reason,
      })
      setTranscriptOpen(true)
    } catch (err) {
      setCallData({ summary: '', transcript: `Error: ${err.message}` })
    } finally {
      setFetchingTranscript(false)
    }
  }

  const fmtDuration = (secs) => {
    if (!secs) return null
    const m = Math.floor(secs / 60), s = Math.round(secs % 60)
    return `${m}m ${s}s`
  }

  return (
    <div className="space-y-8 fade-in-up">
      <div>
        <SectionLabel>Automated Assistance</SectionLabel>
        <h2 className="text-2xl md:text-3xl font-bold text-gray-900">Call the VA</h2>
        <p className="text-gray-500 text-sm leading-relaxed mt-1">
          Our AI agent will call the VA on your behalf and provide a full transcript when the call ends.
        </p>
      </div>

      {/* Consent notice */}
      <div className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <svg className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-0.5">Recording Disclosure</p>
          <p className="text-xs text-amber-700 leading-relaxed">
            This call will be recorded for documentation purposes. The AI agent will announce this disclosure before any
            recording begins. Florida is an all-party consent state — you must stay on the line to confirm consent.
          </p>
        </div>
      </div>

      {/* Phone number input */}
      <div>
        <label className="block text-sm font-semibold text-gray-700 mb-2">Your Phone Number</label>
        <div className="flex items-center gap-2">
          <span className="px-3 py-2.5 rounded-lg border border-gray-200 bg-gray-50 text-sm text-gray-500 font-medium select-none">
            +1
          </span>
          <input
            type="tel"
            placeholder="(555) 867-5309"
            value={phoneInput}
            onChange={e => setPhoneInput(e.target.value)}
            className="flex-1 px-3 py-2.5 rounded-lg border border-gray-200 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200 transition"
          />
        </div>
        {phoneInput && !e164 && (
          <p className="text-xs text-red-500 mt-1">Enter a valid 10-digit US number</p>
        )}
        {e164 && (
          <p className="text-xs text-green-600 mt-1">Vapi will call {e164}</p>
        )}
      </div>

      {errorMsg && (
        <div className="px-4 py-3 rounded-xl text-xs text-red-700 bg-red-50 border border-red-200">{errorMsg}</div>
      )}
      {status === 'success' && (
        <div className="px-4 py-3 rounded-xl text-xs text-green-700 bg-green-50 border border-green-200 space-y-1">
          <p className="font-semibold">Call initiated successfully!</p>
          <p>Vapi is calling {e164} now. Answer it to begin.</p>
        </div>
      )}

      <button
        onClick={handleCall}
        disabled={status === 'loading' || !e164}
        className="w-full py-3 rounded-lg font-semibold text-sm text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        style={{ background: NAV_BLUE }}
        onMouseEnter={e => { if (status !== 'loading' && e164) e.currentTarget.style.background = '#0F2444' }}
        onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
      >
        {status === 'loading'
          ? <><Loader2 className="w-4 h-4 animate-spin" /> Starting Call...</>
          : <><Phone className="w-4 h-4" /> Initiate VA Call</>}
      </button>

      {callInitiated && (
        <div className="space-y-4">
          {!callData && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
              <p className="text-sm text-gray-500 mb-4">After the call ends, click below to load the summary and transcript.</p>
              <button
                onClick={fetchTranscript}
                disabled={fetchingTranscript}
                className="px-6 py-2.5 rounded-lg text-sm font-semibold text-white disabled:opacity-50 transition-colors"
                style={{ background: NAV_BLUE }}
                onMouseEnter={e => { if (!fetchingTranscript) e.currentTarget.style.background = '#0F2444' }}
                onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
              >
                {fetchingTranscript ? 'Loading...' : 'Get Call Summary & Transcript'}
              </button>
            </div>
          )}

          {callData && (
            <div className="space-y-4">
              {(callData.duration_seconds || callData.ended_reason) && (
                <div className="flex gap-4 text-xs text-gray-400">
                  {callData.duration_seconds && <span>Duration: <strong className="text-gray-600">{fmtDuration(callData.duration_seconds)}</strong></span>}
                  {callData.ended_reason && <span>Ended: <strong className="text-gray-600">{callData.ended_reason}</strong></span>}
                </div>
              )}

              {callData.summary ? (
                <div className="bg-white rounded-xl border border-gray-200 p-6">
                  <SectionLabel>Call Summary</SectionLabel>
                  <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap mt-1">{callData.summary}</p>
                </div>
              ) : (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <p className="text-xs text-gray-400">No summary available yet — the call may still be processing.</p>
                </div>
              )}

              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <button
                  onClick={() => setTranscriptOpen(o => !o)}
                  className="w-full flex items-center justify-between px-5 py-4 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <span>Full Transcript</span>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${transcriptOpen ? 'rotate-180' : ''}`} />
                </button>
                {transcriptOpen && (
                  <div className="px-5 pb-5 border-t border-gray-100">
                    <pre className="text-xs text-gray-600 whitespace-pre-wrap leading-relaxed font-sans mt-4">{callData.transcript}</pre>
                  </div>
                )}
              </div>

              <div className="text-center">
                <button onClick={fetchTranscript} disabled={fetchingTranscript}
                  className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-50 flex items-center gap-1.5 mx-auto transition-colors">
                  <RefreshCw className="w-3 h-3" />
                  {fetchingTranscript ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// CHAT
// ─────────────────────────────────────────────
function ChatSection({ jobId, veteranName }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hi! I'm your VA claims advisor. I've reviewed ${veteranName ? `${veteranName}'s` : 'your'} full audit — including ratings, findings, and any call transcripts. What would you like to know?`,
    },
  ])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || streaming) return

    const userMsg = { role: 'user', content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput('')
    setStreaming(true)
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, messages: nextMessages }),
      })

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') { setStreaming(false); return }
          try {
            const token = JSON.parse(payload)
            setMessages(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = {
                ...updated[updated.length - 1],
                content: updated[updated.length - 1].content + token,
              }
              return updated
            })
          } catch (_) {}
        }
      }
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: `Error: ${err.message}` }
        return updated
      })
    } finally {
      setStreaming(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div className="flex flex-col h-full fade-in-up" style={{ minHeight: '0' }}>
      {/* Header */}
      <div className="shrink-0 mb-4">
        <SectionLabel>AI Assistant</SectionLabel>
        <h2 className="text-2xl font-bold text-gray-900">Claims Advisor Chat</h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4 pr-1" style={{ minHeight: 0 }}>
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg flex items-center justify-center mr-2 mt-0.5 shrink-0" style={{ background: NAV_BLUE }}>
                <span className="text-white text-xs font-black">V</span>
              </div>
            )}
            <div
              className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'text-white rounded-br-sm whitespace-pre-wrap'
                  : 'text-gray-800 bg-white border border-gray-200 rounded-bl-sm'
              }`}
              style={msg.role === 'user' ? { background: NAV_BLUE } : {}}
            >
              {msg.role === 'assistant' ? (
                <>
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
                      li: ({ children }) => <li>{children}</li>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                    }}
                  >
                    {msg.content || ''}
                  </ReactMarkdown>
                  {streaming && i === messages.length - 1 && (
                    <span className="inline-block w-1 h-4 bg-gray-400 ml-0.5 animate-pulse align-middle" />
                  )}
                </>
              ) : (
                msg.content || ''
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-gray-200 pt-4 mt-2">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your claim, ratings, appeal options..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:border-transparent leading-relaxed bg-white"
            style={{ maxHeight: '120px', overflowY: 'auto', boxShadow: input ? `0 0 0 2px ${NAV_BLUE}33` : undefined }}
            disabled={streaming}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || streaming}
            className="flex items-center justify-center w-11 h-11 rounded-xl text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
            style={{ background: NAV_BLUE }}
            onMouseEnter={e => { if (input.trim() && !streaming) e.currentTarget.style.background = '#0F2444' }}
            onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
          >
            {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-xs text-gray-300 mt-2 text-center">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// DASHBOARD ROOT
// ─────────────────────────────────────────────
export default function Dashboard({ result, jobId, onNewClaim }) {
  const [activeSection, setActiveSection] = useState('overview')

  const auditResult = result?.audit_result ?? {}
  const flags       = auditResult.flags ?? []
  const vaFormLinks = result?.va_form_links ?? []
  const veteranName = auditResult.veteran_name || ''
  const flagCount   = flags.length

  return (
    <div className="min-h-screen flex flex-col" style={{ background: '#F8FAFC' }}>

      {/* ── Nav ── */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-40 flex items-center h-14 shrink-0">
        {/* Logo — same width as sidebar so they align */}
        <div className="hidden md:flex items-center gap-2 px-5 w-52 shrink-0 border-r border-gray-200 h-full">
          <div className="w-7 h-7 rounded flex items-center justify-center" style={{ background: NAV_BLUE }}>
            <span className="text-white text-xs font-black">V</span>
          </div>
          <span className="font-bold text-lg" style={{ color: NAV_BLUE }}>
            VetClaim <span className="font-normal text-sm" style={{ color: GOLD }}>AI</span>
          </span>
        </div>
        {/* Mobile logo */}
        <div className="flex md:hidden items-center gap-2 px-4">
          <div className="w-7 h-7 rounded flex items-center justify-center" style={{ background: NAV_BLUE }}>
            <span className="text-white text-xs font-black">V</span>
          </div>
          <span className="font-bold text-base" style={{ color: NAV_BLUE }}>VetClaim <span style={{ color: GOLD }}>AI</span></span>
        </div>
        {/* Veteran info + actions */}
        <div className="flex flex-1 items-center justify-between px-6">
          <div className="flex items-center gap-3">
            {veteranName && (
              <>
                <span className="text-sm font-semibold text-gray-700">{veteranName}</span>
                {flagCount > 0 && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full border"
                    style={{ background: '#EEF2FF', borderColor: '#C7D2FE', color: NAV_BLUE }}>
                    {flagCount} Finding{flagCount !== 1 ? 's' : ''}
                  </span>
                )}
              </>
            )}
          </div>
          <button
            onClick={onNewClaim}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold border border-gray-300 text-gray-600 hover:border-gray-400 hover:bg-gray-50 transition-colors"
          >
            + New Claim
          </button>
        </div>
      </nav>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        <aside className="hidden md:flex flex-col w-52 border-r border-gray-200 bg-white pt-5 shrink-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 px-4 mb-2">Navigation</p>
          {NAV_ITEMS.map(({ id, label, Icon }) => {
            const active = activeSection === id
            return (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors text-left mx-2 rounded-lg ${
                  active ? 'text-white' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }`}
                style={active ? { background: NAV_BLUE } : {}}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {label}
              </button>
            )
          })}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto relative">
          <div className={`max-w-3xl mx-auto px-6 md:px-8 py-10 pb-24 md:pb-10 ${activeSection === 'overview' ? '' : 'hidden'}`}>
            <OverviewSection audit={auditResult} result={result} />
          </div>
          <div className={`max-w-3xl mx-auto px-6 md:px-8 py-10 pb-24 md:pb-10 ${activeSection === 'findings' ? '' : 'hidden'}`}>
            <FindingsSection flags={flags} />
          </div>
          <div className={`max-w-3xl mx-auto px-6 md:px-8 py-10 pb-24 md:pb-10 ${activeSection === 'forms' ? '' : 'hidden'}`}>
            <FormsSection vaFormLinks={vaFormLinks} jobId={jobId} />
          </div>
          <div className={`max-w-3xl mx-auto px-6 md:px-8 py-10 pb-24 md:pb-10 ${activeSection === 'vacall' ? '' : 'hidden'}`}>
            <VACallSection />
          </div>
          <div className={`flex flex-col px-6 md:px-8 py-10 pb-24 md:pb-10 h-full ${activeSection === 'chat' ? '' : 'hidden'}`}>
            <div className="max-w-3xl mx-auto w-full flex flex-col flex-1" style={{ minHeight: 0 }}>
              <ChatSection jobId={jobId} veteranName={veteranName} />
            </div>
          </div>
        </main>
      </div>

      {/* Mobile bottom nav */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 flex z-40">
        {NAV_ITEMS.map(({ id, label, Icon }) => {
          const active = activeSection === id
          return (
            <button
              key={id}
              onClick={() => setActiveSection(id)}
              className="flex-1 flex flex-col items-center gap-1 py-2.5 text-xs font-medium transition-colors"
              style={{ color: active ? NAV_BLUE : '#9CA3AF' }}
            >
              <Icon className="w-5 h-5" />
              {label}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
