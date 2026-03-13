'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import type { SectorStat } from '@/lib/types'
import { getSectorColor } from '@/lib/utils'

interface SectorDonutProps {
  data: SectorStat[]
  height?: number
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: SectorStat & { color: string } }> }) {
  if (!active || !payload?.length) return null
  const data = payload[0].payload
  return (
    <div className="bg-surface-raised border border-border rounded-lg px-3 py-2 shadow-glass">
      <p className="text-sm font-medium text-text-primary">{data.sector}</p>
      <p className="text-xs text-text-secondary">
        {data.company_count} companies
      </p>
      {data.avg_founder_age && (
        <p className="text-xs text-text-muted">
          Avg founder age: {data.avg_founder_age}
        </p>
      )}
    </div>
  )
}

export function SectorDonut({ data, height = 280 }: SectorDonutProps) {
  const chartData = data
    .filter(s => s.company_count > 0)
    .slice(0, 8)
    .map(s => ({
      ...s,
      color: getSectorColor(s.sector),
    }))

  const total = chartData.reduce((sum, s) => sum + s.company_count, 0)

  return (
    <div className="flex items-center gap-6">
      <div className="flex-shrink-0" style={{ width: height, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="85%"
              dataKey="company_count"
              strokeWidth={2}
              stroke="#0A0F1E"
            >
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="flex-1 space-y-2">
        {chartData.map((item) => (
          <div key={item.sector} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
            <span className="text-xs text-text-secondary truncate flex-1">
              {item.sector.split('/')[0].trim()}
            </span>
            <span className="text-xs font-mono text-text-primary">
              {Math.round((item.company_count / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
