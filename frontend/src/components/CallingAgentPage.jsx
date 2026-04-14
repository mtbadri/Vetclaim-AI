import { useState } from 'react'

const NAV_BLUE = '#1B3A6B'

export default function CallingAgentPage({ onBack }) {
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState('')
  const [callData, setCallData] = useState(null) // { summary, transcript, duration_seconds, ended_reason }
  const [fetchingTranscript, setFetchingTranscript] = useState(false)
  const [callInitiated, setCallInitiated] = useState(false)
  const [transcriptOpen, setTranscriptOpen] = useState(false)

  const handleCall = async () => {
    setStatus('loading')
    setErrorMsg('')
    setCallData(null)

    try {
      const res = await fetch('/api/call-va', { method: 'POST' })
      const data = await res.json()

      if (!res.ok || data.status === 'error') {
        throw new Error(data.message || data.error || 'Failed to start call')
      }

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
    const m = Math.floor(secs / 60)
    const s = Math.round(secs % 60)
    return `${m}m ${s}s`
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Nav */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
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
          <span className="font-bold text-base" style={{ color: NAV_BLUE }}>VetClaim AI — VA Caller</span>
        </div>
      </nav>

      <main className="flex-1 max-w-xl mx-auto w-full px-6 py-12">

        {/* Heading */}
        <div className="fade-in-up mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">Initiate VA Call</h1>
          <p className="text-gray-500 text-sm leading-relaxed">
            Our AI agent will call the VA representative on your behalf and provide a full transcript when the call ends.
          </p>
        </div>

        {/* Consent notice */}
        <div className="mb-8 p-4 bg-amber-50 border border-amber-200 rounded-lg flex gap-3">
          <svg className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p className="text-xs text-amber-700 leading-relaxed">
            This call will be recorded for documentation purposes. The AI agent will announce
            this disclosure before any recording begins. Florida is an all-party consent state —
            you must stay on the line to confirm consent.
          </p>
        </div>

        {/* Error */}
        {errorMsg && (
          <div className="mb-6 px-4 py-3 rounded-lg text-xs text-red-700 bg-red-50 border border-red-200">
            {errorMsg}
          </div>
        )}

        {/* Success */}
        {status === 'success' && (
          <div className="mb-6 px-4 py-3 rounded-lg text-xs text-green-700 bg-green-50 border border-green-200 space-y-1">
            <p className="font-semibold">Call initiated successfully!</p>
            <p>Vapi is calling your phone now. Answer it to begin.</p>
          </div>
        )}

        {/* Initiate Call button */}
        <div className="fade-in-up-2">
          <button
            onClick={handleCall}
            disabled={status === 'loading'}
            className="w-full py-3 rounded-lg font-semibold text-sm text-white transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: NAV_BLUE }}
            onMouseEnter={e => { if (status !== 'loading') e.currentTarget.style.background = '#0F2444' }}
            onMouseLeave={e => { e.currentTarget.style.background = NAV_BLUE }}
          >
            {status === 'loading' ? (
              <>
                <svg className="w-4 h-4 spin-cw" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Starting Call...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
                </svg>
                Initiate VA Call
              </>
            )}
          </button>
        </div>

        {/* Post-call section */}
        {callInitiated && (
          <div className="mt-8 space-y-4">

            {/* Fetch button */}
            {!callData && (
              <div className="text-center">
                <p className="text-xs text-gray-400 mb-3">
                  After the call ends, click below to load the summary and transcript.
                </p>
                <button
                  onClick={fetchTranscript}
                  disabled={fetchingTranscript}
                  className="px-5 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50"
                  style={{ background: NAV_BLUE }}
                >
                  {fetchingTranscript ? 'Loading...' : 'Get Call Summary & Transcript'}
                </button>
              </div>
            )}

            {callData && (
              <>
                {/* Call meta */}
                <div className="flex gap-3 text-xs text-gray-400">
                  {callData.duration_seconds && (
                    <span>Duration: <strong className="text-gray-600">{fmtDuration(callData.duration_seconds)}</strong></span>
                  )}
                  {callData.ended_reason && (
                    <span>Ended: <strong className="text-gray-600">{callData.ended_reason}</strong></span>
                  )}
                </div>

                {/* Summary card */}
                {callData.summary ? (
                  <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-blue-500 mb-2">Call Summary</p>
                    <p className="text-sm text-blue-900 leading-relaxed whitespace-pre-wrap">{callData.summary}</p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                    <p className="text-xs text-gray-400">No summary available yet — the call may still be processing.</p>
                  </div>
                )}

                {/* Collapsible transcript */}
                <div className="rounded-xl border border-gray-200 overflow-hidden">
                  <button
                    onClick={() => setTranscriptOpen(o => !o)}
                    className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    <span>Full Transcript</span>
                    <svg
                      className={`w-4 h-4 text-gray-400 transition-transform ${transcriptOpen ? 'rotate-180' : ''}`}
                      fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7"/>
                    </svg>
                  </button>
                  {transcriptOpen && (
                    <div className="px-4 pb-4 bg-gray-50 border-t border-gray-100">
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap leading-relaxed font-sans mt-3">
                        {callData.transcript}
                      </pre>
                    </div>
                  )}
                </div>

                {/* Refresh button */}
                <div className="text-center">
                  <button
                    onClick={fetchTranscript}
                    disabled={fetchingTranscript}
                    className="text-xs underline text-gray-400 hover:text-gray-600 disabled:opacity-50"
                  >
                    {fetchingTranscript ? 'Refreshing...' : 'Refresh'}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        <p className="text-center text-xs text-gray-400 mt-10">
          Powered by Vapi · Requires VAPI_PRIVATE_KEY in .env
        </p>
      </main>
    </div>
  )
}
