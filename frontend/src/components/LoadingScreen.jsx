export default function LoadingScreen() {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-10 px-6">

      {/* Icon */}
      <div className="w-16 h-16 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center">
        <svg className="w-7 h-7 text-blue-700" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
      </div>

      {/* Text */}
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900 mb-1">Processing Your Documents</h2>
        <p className="text-gray-500 text-sm">This will only take a moment...</p>
      </div>

      {/* 3-dot conveyor */}
      <div className="relative overflow-hidden" style={{ width: '90px', height: '16px' }}>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="loading-dot absolute rounded-full"
            style={{ left: 0, top: '2px', width: '12px', height: '12px', background: '#1B3A6B' }}
          />
        ))}
      </div>

      {/* Disclaimer */}
      <div className="max-w-md w-full bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-3">
        <svg className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <div>
          <p className="text-xs font-semibold text-amber-800 mb-0.5">Please Note</p>
          <p className="text-xs text-amber-700 leading-relaxed">
            AI can make mistakes. Always verify your claim status and details directly with the VA or a qualified VSO before taking action.
          </p>
        </div>
      </div>
    </div>
  )
}
