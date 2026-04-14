import { useState } from 'react'

const NAV_BLUE = '#1B3A6B'
const GOLD     = '#9B7E2A'

function HeroGraphic() {
  return (
    <div className="flex flex-col items-center gap-4">
      {/* US Flag */}
      <svg viewBox="0 0 380 200" xmlns="http://www.w3.org/2000/svg" className="w-64 md:w-80 rounded shadow-md" style={{ boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}>
        {/* 13 stripes — alternating red/white */}
        {[0,1,2,3,4,5,6,7,8,9,10,11,12].map(i => (
          <rect key={i} x="0" y={i * (200/13)} width="380" height={200/13}
                fill={i % 2 === 0 ? '#B22234' : '#FFFFFF'} />
        ))}
        {/* Blue canton */}
        <rect x="0" y="0" width="152" height={200 * 7/13} fill="#3C3B6E"/>
        {/* 50 stars — 5 rows of 6, 4 rows of 5, staggered */}
        {(() => {
          const stars = []
          const cantonH = 200 * 7/13
          // 9 rows: rows 0,2,4,6,8 have 6 stars; rows 1,3,5,7,9 have 5
          for (let row = 0; row < 9; row++) {
            const count = row % 2 === 0 ? 6 : 5
            const offsetX = row % 2 === 0 ? 12 : 24
            for (let col = 0; col < count; col++) {
              const x = offsetX + col * 24
              const y = 10 + row * (cantonH / 10)
              stars.push(
                <text key={`${row}-${col}`} x={x} y={y} textAnchor="middle"
                      fontSize="9" fill="white" dominantBaseline="middle">★</text>
              )
            }
          }
          return stars
        })()}
      </svg>

      {/* Soldier silhouette */}
      <svg viewBox="0 0 160 200" xmlns="http://www.w3.org/2000/svg" className="w-28 md:w-36">
        {/* Ground line */}
        <line x1="20" y1="192" x2="140" y2="192" stroke="#CBD5E1" strokeWidth="2"/>

        {/* Left boot */}
        <rect x="54" y="178" width="16" height="14" rx="3" fill="#374151"/>
        <rect x="50" y="186" width="22" height="8" rx="3" fill="#1F2937"/>
        {/* Right boot */}
        <rect x="90" y="178" width="16" height="14" rx="3" fill="#374151"/>
        <rect x="88" y="186" width="22" height="8" rx="3" fill="#1F2937"/>

        {/* Legs */}
        <rect x="56" y="148" width="16" height="34" rx="4" fill="#4B5563"/>
        <rect x="88" y="148" width="16" height="34" rx="4" fill="#4B5563"/>

        {/* Belt */}
        <rect x="50" y="144" width="60" height="8" rx="3" fill="#374151"/>
        <rect x="74" y="145" width="12" height="6" rx="1" fill="#9B7E2A"/>

        {/* Torso / BDU jacket */}
        <path d="M50,100 L46,144 L114,144 L110,100 Q92,94 80,94 Q68,94 50,100Z" fill="#4B5563"/>
        {/* Jacket pocket left */}
        <rect x="55" y="108" width="18" height="14" rx="2" fill="#374151" opacity="0.6"/>
        {/* Jacket pocket right */}
        <rect x="87" y="108" width="18" height="14" rx="2" fill="#374151" opacity="0.6"/>
        {/* US flag patch on left shoulder */}
        <rect x="51" y="102" width="18" height="10" rx="1" fill="#B22234"/>
        {[0,1,2].map(i => (
          <rect key={i} x="51" y={102 + i * 3.3} width="18" height={3.3}
                fill={i % 2 === 0 ? '#B22234' : '#FFFFFF'} opacity="0.9"/>
        ))}
        <rect x="51" y="102" width="7" height="6" rx="0" fill="#3C3B6E"/>

        {/* Left arm */}
        <path d="M50,100 Q30,112 28,136 Q36,140 42,136 Q46,114 56,104Z" fill="#4B5563"/>
        {/* Right arm — saluting */}
        <path d="M110,100 Q128,88 138,76 Q133,70 128,74 Q120,84 108,96Z" fill="#4B5563"/>
        {/* Right hand at brow */}
        <ellipse cx="130" cy="73" rx="8" ry="6" fill="#D4A574" transform="rotate(-30 130 73)"/>

        {/* Neck */}
        <rect x="74" y="88" width="12" height="14" rx="4" fill="#D4A574"/>

        {/* Head */}
        <ellipse cx="80" cy="78" rx="18" ry="20" fill="#D4A574"/>
        {/* Ear left */}
        <ellipse cx="62" cy="79" rx="4" ry="5" fill="#C49060"/>
        {/* Ear right */}
        <ellipse cx="98" cy="79" rx="4" ry="5" fill="#C49060"/>
        {/* Eyes */}
        <ellipse cx="73" cy="76" rx="3" ry="3.5" fill="#1F2937"/>
        <ellipse cx="87" cy="76" rx="3" ry="3.5" fill="#1F2937"/>
        <circle cx="72" cy="75" r="1" fill="white" opacity="0.6"/>
        <circle cx="86" cy="75" r="1" fill="white" opacity="0.6"/>
        {/* Mouth — slight neutral expression */}
        <path d="M74,87 Q80,90 86,87" fill="none" stroke="#B07848" strokeWidth="1.5" strokeLinecap="round"/>

        {/* Combat helmet */}
        <ellipse cx="80" cy="62" rx="22" ry="14" fill="#374151"/>
        <path d="M58,64 Q80,54 102,64" fill="#374151" stroke="#374151" strokeWidth="1"/>
        {/* Helmet brim */}
        <path d="M56,66 Q80,60 104,66" fill="none" stroke="#1F2937" strokeWidth="3" strokeLinecap="round"/>
        {/* Helmet cover texture lines */}
        <path d="M62,60 Q80,56 98,60" fill="none" stroke="#4B5563" strokeWidth="1" opacity="0.5"/>
        <path d="M64,65 Q80,61 96,65" fill="none" stroke="#4B5563" strokeWidth="1" opacity="0.5"/>
      </svg>
    </div>
  )
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-lg w-full p-8 shadow-xl border border-gray-200 fade-in-up">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none transition-colors">&times;</button>
        </div>
        {children}
      </div>
    </div>
  )
}

export default function LandingPage({ onUploadClick }) {
  const [modal, setModal] = useState(null)

  return (
    <div className="min-h-screen bg-white flex flex-col">

      {/* ── Nav ── */}
      <nav className="border-b border-gray-200 bg-white sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: NAV_BLUE }}>
              <span className="text-white text-xs font-black">V</span>
            </div>
            <span className="font-bold text-xl" style={{ color: NAV_BLUE }}>
              VetClaim <span className="font-normal text-base" style={{ color: GOLD }}>AI</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <button onClick={() => setModal('how')} className="text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium">
              How It Works
            </button>
            <button onClick={() => setModal('about')} className="text-sm text-gray-600 hover:text-gray-900 transition-colors font-medium">
              About
            </button>
            <button
              onClick={onUploadClick}
              className="px-5 py-2 rounded-lg text-sm font-semibold text-white transition-colors"
              style={{ background: NAV_BLUE }}
              onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
              onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
            >
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="flex-1 max-w-6xl mx-auto px-6 py-16 md:py-24 flex flex-col md:flex-row items-center gap-12 md:gap-16">
        {/* Left */}
        <div className="flex-1 fade-in-up">
          <span className="inline-block px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider mb-5"
                style={{ background: '#EEF2FF', color: NAV_BLUE }}>
            For U.S. Veterans
          </span>
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-5" style={{ color: '#0F2444' }}>
            Navigate Your VA Disability Claim with Confidence
          </h1>
          <p className="text-gray-600 text-lg leading-relaxed mb-8 max-w-lg">
            VetClaim AI reviews your VA documents, identifies gaps in your evidence, and helps you understand your claim — so you can get the benefits you've earned.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={onUploadClick}
              className="px-7 py-3 rounded-lg font-semibold text-white text-sm transition-colors"
              style={{ background: NAV_BLUE }}
              onMouseEnter={e => e.currentTarget.style.background = '#0F2444'}
              onMouseLeave={e => e.currentTarget.style.background = NAV_BLUE}
            >
              Upload Documents
            </button>
            <button
              onClick={() => setModal('how')}
              className="px-7 py-3 rounded-lg font-semibold text-sm border border-gray-300 text-gray-700 hover:border-gray-400 hover:bg-gray-50 transition-colors"
            >
              How It Works
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-5">
            Not affiliated with the U.S. Department of Veterans Affairs. Always consult an accredited VSO.
          </p>
        </div>

        {/* Right — Flag + Soldier */}
        <div className="fade-in-up-2 flex justify-center">
          <HeroGraphic />
        </div>
      </section>

      {/* ── Feature row ── */}
      <section className="border-t border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 py-14 fade-in-up-3">
          <h2 className="text-xl font-bold text-gray-900 mb-8 text-center">What VetClaim AI Reviews</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { icon: '📋', label: 'C&P Exam Reports', desc: 'Analyze Compensation & Pension exam results for supporting findings.' },
              { icon: '📄', label: 'DBQ Forms', desc: 'Review Disability Benefits Questionnaires for completeness and nexus.' },
              { icon: '⚖️', label: 'Rating Decisions', desc: 'Identify the rationale behind your current VA rating.' },
              { icon: '📞', label: 'VA Status Calls', desc: 'Automated call to request a claim status update from the VA.' },
            ].map(({ icon, label, desc }) => (
              <div key={label} className="bg-white rounded-xl p-5 border border-gray-200">
                <div className="text-2xl mb-3">{icon}</div>
                <p className="font-semibold text-gray-900 text-sm mb-1">{label}</p>
                <p className="text-gray-500 text-xs leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <span className="font-semibold text-sm" style={{ color: NAV_BLUE }}>VetClaim AI</span>
          <p className="text-xs text-gray-400 text-center">
            VetClaim AI is a document preparation tool and does not provide legal or medical advice.
          </p>
          <div className="flex gap-5">
            <button onClick={() => setModal('how')} className="text-xs text-gray-500 hover:text-gray-800 transition-colors">How It Works</button>
            <button onClick={() => setModal('about')} className="text-xs text-gray-500 hover:text-gray-800 transition-colors">About</button>
          </div>
        </div>
      </footer>

      {/* ── How It Works Modal ── */}
      {modal === 'how' && (
        <Modal title="How It Works" onClose={() => setModal(null)}>
          <div className="space-y-5">
            {[
              { step: '1', title: 'Upload Your Documents', desc: 'Submit your C&P Exam, DBQ forms, and VA Rating Decision or Denial Letter.' },
              { step: '2', title: 'AI Reviews Everything', desc: 'Our system analyzes your documents for key findings, nexus opportunities, and evidence gaps.' },
              { step: '3', title: 'Track Your Claim', desc: 'Follow along as your claim moves through review — and call the VA directly from the app.' },
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex gap-4 items-start">
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold text-white"
                     style={{ background: NAV_BLUE }}>
                  {step}
                </div>
                <div>
                  <p className="text-gray-900 font-semibold mb-1 text-sm">{title}</p>
                  <p className="text-gray-500 text-sm leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </Modal>
      )}

      {/* ── About Modal ── */}
      {modal === 'about' && (
        <Modal title="About VetClaim AI" onClose={() => setModal(null)}>
          <div className="space-y-4 text-gray-600 text-sm leading-relaxed">
            <p>VetClaim AI was built to help veterans navigate the often confusing VA benefits claims process — so you can focus on your health and life, not paperwork.</p>
            <p>Our team is dedicated to making sure every veteran gets the benefits they've earned through their service and sacrifice.</p>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-xs text-gray-500 leading-relaxed">
              VetClaim AI is a document preparation and analysis tool. It does not provide legal or medical advice. For official claims, work with an accredited VSO, attorney, or claims agent.
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
