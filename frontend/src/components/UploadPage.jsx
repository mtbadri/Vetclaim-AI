import { useState, useRef } from 'react'

const NAV_BLUE = '#1B3A6B'

const DEMO_CASES = [
  {
    id: 'arina-kiera',
    name: 'Arina Kiera',
    conditions: 'PTSD · Narcolepsy · CFS',
    docs: [
      'C&P_Examination_Arina_Kiera_10052025.pdf',
      'DBQ_CFS_Arina_Kiera.pdf',
      'DBQ_Narcolepsy_Arina_Kiera.pdf',
      'DBQ_PTSD_Arina_Kiera.pdf',
      'Rating_Decision_Arina_Kiera_11012025.pdf',
    ],
  },
  {
    id: 'james_millner',
    name: 'James Millner',
    conditions: 'ALS · Hearing Loss',
    docs: [
      'C&P_Exam_Combined_DBQs.pdf',
      'DBQ_ALS_James_Milner_SAMPLE.pdf',
      'james_miller_decision_letter.pdf',
      'james_miller_ear_dbq.pdf',
      'james_miller_personal_statement.pdf',
    ],
  },
  {
    id: 'robert-graza',
    name: 'Robert Garza',
    conditions: 'Amputation · Arthritis · PTSD',
    docs: [
      'CP_Exam_Robert_Garza_SAMPLE.pdf',
      'DBQ_Amputation_Robert_Garza_SAMPLE.pdf',
      'DBQ_Arthritis_Robert_Garza_SAMPLE.pdf',
      'DBQ_PTSD_Robert_Garza_SAMPLE.pdf',
      'Rating_Decision_Robert_Garza_SAMPLE.pdf',
    ],
  },
]

export default function UploadPage({ onBack, onSubmit, error }) {
  const [files, setFiles] = useState([])
  const [loadingDemo, setLoadingDemo] = useState(null)
  const [demoError, setDemoError] = useState(null)
  const fileInputRef = useRef()

  const handleFile = (newFiles) => {
    setFiles(prev => [...prev, ...Array.from(newFiles)])
  }

  const removeFile = (index) => setFiles(prev => prev.filter((_, i) => i !== index))

  const loadDemoCase = async (demo) => {
    setLoadingDemo(demo.id)
    setDemoError(null)
    try {
      const fetched = await Promise.all(
        demo.docs.map(async (name) => {
          const url = `/testcases/${demo.id}/${encodeURIComponent(name)}`
          const res = await fetch(url)
          if (!res.ok) throw new Error(`Could not load ${name}`)
          const blob = await res.blob()
          return new File([blob], name, { type: 'application/pdf' })
        })
      )
      setFiles(fetched)
    } catch (e) {
      setDemoError(e.message)
    } finally {
      setLoadingDemo(null)
    }
  }

  const fmtSize = (b) => b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1024 / 1024).toFixed(2)} MB`

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* Nav */}
      <nav className="border-b border-gray-200 bg-white">
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
          <span className="font-bold text-base" style={{ color: NAV_BLUE }}>VetClaim AI</span>
        </div>
      </nav>

      <main className="flex-1 max-w-2xl mx-auto w-full px-6 py-12">

        {/* Heading */}
        <div className="fade-in-up mb-8">
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: NAV_BLUE }}>
            Step 1 of 3
          </p>
          <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
            Upload Your VA Documents
          </h1>
          <p className="text-gray-500 text-sm leading-relaxed">
            Upload your C&P Exam, DBQ, Rating Decision, or any other VA-related documents.
          </p>
        </div>

        {/* Browse area */}
        <div className="fade-in-up-2 mb-6">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={(e) => handleFile(e.target.files)}
          />
          <button
            onClick={() => fileInputRef.current.click()}
            className="w-full py-10 rounded-xl border-2 border-dashed border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100 transition-colors flex flex-col items-center gap-3 text-gray-500 hover:text-gray-700"
          >
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
            </svg>
            <div className="text-center">
              <p className="text-sm font-semibold text-gray-700">Click to browse files</p>
              <p className="text-xs text-gray-400 mt-0.5">Any file type accepted</p>
            </div>
          </button>
        </div>

        {/* Demo cases */}
        <div className="fade-in-up-2 mb-6">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Or try a demo case
          </p>
          {demoError && (
            <p className="text-xs text-red-500 mb-2">{demoError}</p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {DEMO_CASES.map((demo) => (
              <button
                key={demo.id}
                onClick={() => loadDemoCase(demo)}
                disabled={loadingDemo !== null}
                className="text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-gray-400 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-wait"
              >
                <p className="text-sm font-semibold text-gray-800 mb-0.5">
                  {loadingDemo === demo.id ? 'Loading…' : demo.name}
                </p>
                <p className="text-xs text-gray-400">{demo.conditions}</p>
                <p className="text-xs text-gray-300 mt-1">{demo.docs.length} documents</p>
              </button>
            ))}
          </div>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="fade-in-up mb-8">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              {files.length} file{files.length !== 1 ? 's' : ''} selected
            </p>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {files.map((file, idx) => (
                <div key={idx} className="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 bg-white">
                  <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/>
                  </svg>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 font-medium truncate">{file.name}</p>
                    <p className="text-xs text-gray-400">{fmtSize(file.size)}</p>
                  </div>
                  <button
                    onClick={() => removeFile(idx)}
                    className="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upload error */}
        {error && (
          <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-sm font-semibold text-red-700">Upload failed</p>
            <p className="text-xs text-red-500 mt-0.5">{error}</p>
          </div>
        )}

        {/* Submit */}
        <div className="fade-in-up-3">
          <button
            disabled={files.length === 0}
            onClick={() => onSubmit(files)}
            className="w-full py-3 rounded-lg font-semibold text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed text-white"
            style={{ background: NAV_BLUE }}
            onMouseEnter={e => { if (!e.currentTarget.disabled) e.currentTarget.style.background = '#0F2444' }}
            onMouseLeave={e => { e.currentTarget.style.background = NAV_BLUE }}
          >
            {files.length > 0 ? `Submit ${files.length} File${files.length !== 1 ? 's' : ''}` : 'Select files to continue'}
          </button>
        </div>
      </main>
    </div>
  )
}
