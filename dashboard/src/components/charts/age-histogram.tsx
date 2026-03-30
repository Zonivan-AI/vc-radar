'use client'

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import type { AgeBucket } from '@/lib/types'

interface AgeHistogramProps {
  data: AgeBucket[]
  height?: number
  showLabels?: boolean
}

const GRADIENT_COLORS = [
  '#D97706', '#CA6F06', '#B45309', '#A34A08',
  '#924107', '#813806', '#703005', '#5F2804',
]

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: AgeBucket }> }) {
  if (!active || !payload?.length) return null
  const data = payload[0].payload
  return (
    <div className="bg-surface-raised border border-border rounded-lg px-3 py-2 shadow-glass">
      <p className="text-sm font-medium text-text-primary">Age {data.age_bucket}</p>
      <p className="text-xs text-text-secondary">
        {data.count} founders ({data.percentage}%)
      </p>
    </div>
  )
}

export function AgeHistogram({ data, height = 300, showLabels = true }: AgeHistogramProps) {
  return (
    <div style={{ minHeight: height }}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1F2937" />
          <XAxis
            dataKey="age_bucket"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            axisLine={{ stroke: '#1F2937' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={50}>
            {data.map((_, i) => (
              <Cell key={i} fill={GRADIENT_COLORS[i % GRADIENT_COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      {showLabels && (
        <div className="flex items-center justify-center gap-6 mt-3 text-xs text-text-secondary">
          <span className="text-center">Age at Founding</span>
        </div>
      )}
    </div>
  )
}
