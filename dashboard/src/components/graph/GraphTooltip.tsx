'use client'

import type { GraphNode } from '@/lib/graph-types'
import { getNodeTooltipInfo } from '@/lib/graph-data'

interface GraphTooltipProps {
  node: GraphNode | null
  position: { x: number; y: number } | null
}

export function GraphTooltip({ node, position }: GraphTooltipProps) {
  if (!node || !position) return null

  const info = getNodeTooltipInfo(node)
  const dotColor = node.type === 'vc' ? '#7C8FFF' : '#38BDF8'

  return (
    <div
      className="fixed z-50 pointer-events-none animate-scale-in"
      style={{
        left: Math.min(position.x + 14, (typeof window !== 'undefined' ? window.innerWidth : 1600) - 300),
        top: Math.min(position.y + 14, (typeof window !== 'undefined' ? window.innerHeight : 900) - 220),
      }}
    >
      <div className="glass-panel-strong p-5 min-w-[240px] max-w-[300px]">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: dotColor }} />
          <span className="text-[13px] font-semibold text-[#E2E8F0]">{info.title}</span>
        </div>
        <p className="text-xs text-[#94A3B8] mb-3 pl-4">{info.subtitle}</p>

        {/* Metrics */}
        {info.details.length > 0 && (
          <div className="space-y-1.5 pl-4">
            {info.details.map((detail, i) => (
              <p key={i} className="text-xs text-[#64748B]">{detail}</p>
            ))}
          </div>
        )}

        {/* Hint */}
        <p className="text-[10px] text-[#475569] mt-3 pl-4">Click to explore →</p>
      </div>
    </div>
  )
}
