'use client'

import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'

const LEGEND_ITEMS = [
  { label: 'VC Firm', color: '#B45309', size: 'w-2.5 h-2.5' },
  { label: 'Fintech', color: '#3B82F6', size: 'w-2 h-2' },
  { label: 'AI/ML', color: '#8B5CF6', size: 'w-2 h-2' },
  { label: 'SaaS', color: '#D97706', size: 'w-2 h-2' },
  { label: 'Healthcare', color: '#EC4899', size: 'w-2 h-2' },
  { label: 'Consumer', color: '#F97316', size: 'w-2 h-2' },
  { label: 'Climate', color: '#22C55E', size: 'w-2 h-2' },
]

export function GraphLegend() {
  const [expanded, setExpanded] = useState(false)

  const visibleItems = expanded ? LEGEND_ITEMS : LEGEND_ITEMS.slice(0, 4)

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
      <div
        className="glass-panel px-5 py-2.5 flex items-center gap-4 text-[11px] text-[#78716C]"
        style={{ borderRadius: '20px' }}
      >
        {visibleItems.map(item => (
          <span key={item.label} className="flex items-center gap-1.5">
            <span
              className={`${item.size} rounded-full inline-block`}
              style={{
                backgroundColor: item.color,
                boxShadow: `0 0 6px ${item.color}66`,
              }}
            />
            {item.label}
          </span>
        ))}

        {/* Divider */}
        <span className="w-px h-3 bg-white/[0.06]" />

        {/* Investment link */}
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-px inline-block" style={{ backgroundColor: '#B4530940' }} />
          Investment
        </span>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="ml-1 text-[#A8A29E] hover:text-[#78716C] transition-colors"
        >
          {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
        </button>
      </div>
    </div>
  )
}
