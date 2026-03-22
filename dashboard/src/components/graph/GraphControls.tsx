'use client'

import { RotateCcw, ZoomIn, ZoomOut } from 'lucide-react'

interface GraphControlsProps {
  onResetView: () => void
  onZoomIn: () => void
  onZoomOut: () => void
}

export function GraphControls({ onResetView, onZoomIn, onZoomOut }: GraphControlsProps) {
  const btnClass =
    'w-11 h-11 flex items-center justify-center text-[#64748B] hover:text-[#E2E8F0] transition-colors'

  return (
    <div className="fixed bottom-6 right-6 z-40">
      <div className="glass-panel flex items-center overflow-hidden" style={{ borderRadius: '28px' }}>
        <button className={btnClass} onClick={onResetView} title="Reset View">
          <RotateCcw className="w-4 h-4" />
        </button>
        <div className="w-px h-5 bg-white/[0.06]" />
        <button className={btnClass} onClick={onZoomIn} title="Zoom In">
          <ZoomIn className="w-4 h-4" />
        </button>
        <div className="w-px h-5 bg-white/[0.06]" />
        <button className={btnClass} onClick={onZoomOut} title="Zoom Out">
          <ZoomOut className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
