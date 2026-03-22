'use client'

export function GraphLegend() {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
      <div className="glass-panel px-5 py-2 flex items-center gap-5 text-[11px] text-[#64748B]" style={{ borderRadius: '20px' }}>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: '#7C8FFF' }} />
          VC Firm
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: '#38BDF8' }} />
          Company
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-px inline-block" style={{ backgroundColor: '#7C8FFF80' }} />
          Investment
        </span>
      </div>
    </div>
  )
}
