'use client'

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { CHART_COLORS } from '@/lib/utils'

interface TrendDataPoint {
  year: number
  [sector: string]: number
}

interface TrendChartProps {
  data: TrendDataPoint[]
  sectors: string[]
  height?: number
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-raised border border-border rounded-lg px-3 py-2 shadow-glass">
      <p className="text-sm font-medium text-text-primary mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-text-secondary">{entry.name}:</span>
          <span className="text-text-primary font-mono">{entry.value}</span>
        </div>
      ))}
    </div>
  )
}

export function TrendChart({ data, sectors, height = 350 }: TrendChartProps) {
  return (
    <div style={{ minHeight: height }}>
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <defs>
          {sectors.map((sector, i) => (
            <linearGradient key={sector} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1F2937" />
        <XAxis
          dataKey="year"
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
          axisLine={{ stroke: '#1F2937' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
          iconType="circle"
          iconSize={8}
        />
        {sectors.map((sector, i) => (
          <Area
            key={sector}
            type="monotone"
            dataKey={sector}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            fill={`url(#grad-${i})`}
            strokeWidth={2}
            stackId="1"
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
    </div>
  )
}
