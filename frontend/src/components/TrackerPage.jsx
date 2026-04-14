import { useState, useEffect } from 'react'

const NAV_BLUE = '#1B3A6B'

const STAGES = [
  {
    id: 0,
    title: 'Documents Received',
    desc: 'Your PDFs have been securely uploaded and queued for processing.',
  },
  {
    id: 1,
    title: 'Extracting Claim Data',
    desc: 'Parsing your C&P Exam, DBQ forms, and Rating Decisions to pull out disability conditions, assigned ratings, and diagnostic codes.',
  },
  {
    id: 2,
    title: 'AI Audit Running',
    desc: 'Claude AI is cross-referencing your conditions against 38 CFR Part 4, PACT Act eligibility rules, combined rating math, and TDIU criteria.',
  },
  {
    id: 3,
    title: 'Pre-Filling VA Forms',
    desc: 'Generating pre-filled appeal forms (21-526EZ, 20-0995, 20-0996) based on the findings from your audit.',
  },
  {
    id: 4,
    title: 'Audit Complete',
    desc: 'Your full report is ready — corrected ratings, potential benefit increases, and downloadable forms.',
  },
]

export default function TrackerPage({ files, jobId, onBack, onViewAudit }) {
  const [activeStage, setActiveStage] = useState(0)
  const [completedStages, setCompletedStages] = useState(new Set([0]))
  const [pipelineResult, setPipelineResult] = useState(null)
  const [pipelineError, setPipelineError] = useState(null)

  useEffect(() => {
    if (!jobId) {
      // No real job — fall back to demo simulation
      const timers = [
        setTimeout(() => { setActiveStage(1); setCompletedStages(new Set([0])) }, 800),
        setTimeout(() => { setActiveStage(2); setCompletedStages(new Set([0, 1])) }, 3000),
        setTimeout(() => { setActiveStage(3); setCompletedStages(new Set([0, 1, 2])) }, 5500),
        setTimeout(() => { setActiveStage(4); setCompletedStages(new Set([0, 1, 2, 3])) }, 7500),
        setTimeout(() => { setCompletedStages(new Set([0, 1, 2, 3, 4])) }, 9000),
      ]
      return () => timers.forEach(clearTimeout)
    }

    // Connect to the real SSE pipeline stream
    const es = new EventSource(`/api/stream/${jobId}`)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        const { step } = data

        if (step === 'parsing_documents') {
          setActiveStage(1)
          setCompletedStages(new Set([0]))
        } else if (step === 'running_audit') {
          setActiveStage(2)
          setCompletedStages(new Set([0, 1]))
        } else if (step === 'filling_forms') {
          setActiveStage(3)
          setCompletedStages(new Set([0, 1, 2]))
        } else if (step === 'complete') {
          setActiveStage(4)
          setCompletedStages(new Set([0, 1, 2, 3]))
          es.close()
          // Poll until result is ready (may be 202 for a moment)
          const poll = () => {
            fetch(`/api/result/${jobId}`)
              .then(r => {
                if (r.status === 202) { setTimeout(poll, 1500); return null }
                return r.ok ? r.json() : Promise.reject(r.status)
              })
              .then(result => {
                if (result) {
                  setPipelineResult(result)
                  setCompletedStages(new Set([0, 1, 2, 3, 4]))
                }
              })
              .catch(() => setPipelineError('Could not load audit results.'))
          }
          poll()
        } else if (step === 'error') {
          setPipelineError(data.status || 'An error occurred during processing.')
          es.close()
        }
      } catch (_) { /* ignore malformed events */ }
    }

    es.onerror = () => {
      setPipelineError('Lost connection to server. Please try again.')
      es.close()
    }

    return () => es.close()
  }, [jobId])

  // Auto-redirect to results as soon as the result is loaded
  useEffect(() => {
    if (pipelineResult) {
      onViewAudit(pipelineResult)
    }
  }, [pipelineResult])

  const allDone = completedStages.size === 5
  const fileCount = Array.isArray(files) ? files.length : 0

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
            style={allDone
              ? { background: '#F0FDF4', color: '#166534', border: '1px solid #BBF7D0' }
              : { background: '#EFF6FF', color: '#1D4ED8', border: '1px solid #BFDBFE' }}
          >
            {allDone ? 'Review Complete' : 'Processing...'}
          </span>
        </div>
      </nav>

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-12">

        {/* Heading */}
        <div className="fade-in-up mb-8">
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-1">Claim Progress</h1>
          <p className="text-gray-500 text-sm">
            {fileCount} file{fileCount !== 1 ? 's' : ''} submitted
            &nbsp;·&nbsp;
            {allDone ? 'All steps complete' : 'Review in progress'}
          </p>
        </div>

        {/* ── Stepper ── */}
        <div className="fade-in-up-2 mb-10">
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-4 top-8 bottom-8 w-px bg-gray-200" />

            <div className="space-y-4">
              {STAGES.map((stage) => {
                const isDone    = completedStages.has(stage.id)
                const isActive  = activeStage === stage.id && !isDone
                const isPending = !isDone && !isActive

                return (
                  <div
                    key={stage.id}
                    className="relative flex gap-5 items-start transition-opacity duration-500"
                    style={{ opacity: isPending ? 0.35 : 1 }}
                  >
                    {/* Circle */}
                    <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold transition-all duration-500 ${
                      isDone    ? 'bg-green-600 text-white' :
                      isActive  ? 'bg-blue-600 text-white' :
                                  'bg-white border-2 border-gray-300 text-gray-400'
                    }`}>
                      {isDone ? (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/>
                        </svg>
                      ) : isActive ? (
                        <svg className="w-4 h-4 spin-cw" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                        </svg>
                      ) : stage.id + 1}
                    </div>

                    {/* Card */}
                    <div className={`flex-1 rounded-lg px-5 py-4 border transition-all duration-500 ${
                      isDone   ? 'bg-green-50 border-green-200' :
                      isActive ? 'bg-blue-50 border-blue-200' :
                                 'bg-white border-gray-200'
                    }`}>
                      <div className="flex items-center justify-between mb-1">
                        <p className={`font-semibold text-sm ${
                          isDone ? 'text-green-800' : isActive ? 'text-blue-800' : 'text-gray-400'
                        }`}>
                          {stage.title}
                        </p>
                        {isDone   && <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-0.5 rounded-full">Done</span>}
                        {isActive && <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full animate-pulse">In Progress</span>}
                        {isPending && <span className="text-xs text-gray-400">Pending</span>}
                      </div>
                      <p className={`text-xs leading-relaxed ${
                        isDone ? 'text-green-700' : isActive ? 'text-blue-700' : 'text-gray-400'
                      }`}>
                        {stage.desc}
                      </p>
                      {isActive && (
                        <div className="mt-3 h-1 bg-blue-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full tracker-fill" />
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* ── Pipeline error ── */}
        {pipelineError && (
          <div className="mb-6 border border-red-200 bg-red-50 rounded-xl p-5 text-center">
            <p className="text-red-700 font-semibold text-sm mb-1">Processing Error</p>
            <p className="text-red-500 text-xs">{pipelineError}</p>
            <button
              onClick={onBack}
              className="mt-3 text-xs text-gray-500 hover:text-gray-800 underline"
            >
              ← Back to Home
            </button>
          </div>
        )}

        {/* ── All done ── */}
        {allDone && !pipelineError && (
          <div className="fade-in-up bg-green-50 border border-green-200 rounded-xl p-6 text-center mb-6">
            <div className="text-3xl mb-3">🎖️</div>
            <h3 className="text-base font-bold text-green-900 mb-1">Review Complete</h3>
            <p className="text-green-700 text-sm mb-5">
              Your AI audit is ready. View your full report to see findings, corrected ratings,
              and pre-filled VA appeal forms.
            </p>

            {pipelineResult ? (
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => onViewAudit && onViewAudit(pipelineResult)}
                  className="px-7 py-2.5 rounded-lg font-semibold text-sm text-white transition-colors"
                  style={{ background: NAV_BLUE }}
                  onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
                  onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
                >
                  View Full Audit →
                </button>
                <button
                  onClick={onBack}
                  className="px-7 py-2.5 rounded-lg font-semibold text-sm text-gray-600 border border-gray-300 hover:bg-gray-50 transition-colors"
                >
                  Back to Home
                </button>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-2 text-green-700 text-sm">
                <svg className="w-4 h-4 spin-cw" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Loading your audit report…
              </div>
            )}
          </div>
        )}

        {!allDone && !pipelineError && (
          <div className="text-center">
            <button
              onClick={onBack}
              className="text-xs text-gray-400 hover:text-gray-700 transition-colors"
            >
              ← Back to Home
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
