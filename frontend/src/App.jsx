import { useState, useEffect } from 'react'
import LandingPage from './components/LandingPage'
import UploadPage from './components/UploadPage'
import LoadingScreen from './components/LoadingScreen'
import TrackerPage from './components/TrackerPage'
import Dashboard from './components/Dashboard'

const SESSION_KEY = 'vetclaim_session'

function saveSession(data) {
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(data)) } catch (_) {}
}

function clearSession() {
  try { localStorage.removeItem(SESSION_KEY) } catch (_) {}
}

function loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || 'null') } catch (_) { return null }
}

export default function App() {
  const [page, setPage] = useState('landing')
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [jobId, setJobId] = useState(null)
  const [auditResult, setAuditResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)

  // Restore session on mount
  useEffect(() => {
    const saved = loadSession()
    if (!saved) return
    if (saved.auditResult) {
      setAuditResult(saved.auditResult)
      setJobId(saved.jobId ?? null)
      setPage('dashboard')
    } else if (saved.jobId) {
      setJobId(saved.jobId)
      setPage('tracker')
    }
  }, [])

  // Persist session whenever jobId or auditResult changes
  useEffect(() => {
    if (jobId || auditResult) {
      saveSession({ jobId, auditResult })
    }
  }, [jobId, auditResult])

  const handleSubmit = async (files) => {
    setUploadedFiles(files)
    setUploadError(null)
    setAuditResult(null)
    clearSession()
    setPage('loading')

    const formData = new FormData()
    files.forEach(f => formData.append('files', f))

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: formData })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.error || `Upload failed (${res.status})`)
      }
      const { job_id } = await res.json()
      setJobId(job_id)
      setPage('tracker')
    } catch (err) {
      setUploadError(err.message)
      setPage('upload')
    }
  }

  const handleViewAudit = (result) => {
    setAuditResult(result)
    setPage('dashboard')
  }

  const handleGoHome = () => {
    clearSession()
    setJobId(null)
    setAuditResult(null)
    setPage('landing')
  }

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {page === 'landing' && (
        <LandingPage
          onUploadClick={() => setPage('upload')}
          onCallClick={() => setPage('upload')}
        />
      )}
      {page === 'upload' && (
        <UploadPage
          onBack={() => setPage('landing')}
          onSubmit={handleSubmit}
          error={uploadError}
        />
      )}
      {page === 'loading' && <LoadingScreen />}
      {page === 'tracker' && (
        <TrackerPage
          files={uploadedFiles}
          jobId={jobId}
          onBack={handleGoHome}
          onViewAudit={handleViewAudit}
        />
      )}
      {page === 'dashboard' && (
        <Dashboard
          result={auditResult}
          jobId={jobId}
          onNewClaim={handleGoHome}
        />
      )}
    </div>
  )
}
