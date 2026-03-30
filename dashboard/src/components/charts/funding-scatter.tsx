'use client'

import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ZAxis
} from 'recharts'
import { getSectorColor, formatCurrency } from '@/lib/utils'
import type { Founder, Company } from '@/lib/types'

interface FundingScatterProps {
  founders: Founder[]
  companies: Company[]
  height?: number
}

interface ScatterPoint {
  x: number
  y: number
  z: number
  name: string
  company: string
  sector: string
  color: string
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ScatterPoint }> }) {
  if (!active || !payload?.length) return null
  const data = payload[0].payload
  return (
    <div className="bg-surface-raised border border-border rounded-lg px-3 py-2 shadow-glass">
      <p className="text-sm font-medium text-text-primary">{data.name}</p>
      <p className="text-xs text-accent">{data.company}</p>
      <p className="text-xs text-text-secondary">
        Age at founding: {data.x} | Exp: {data.y} yrs
      </p>
      <p className="text-xs text-text-muted">{data.sector}</p>
    </div>
  )
}

export function FundingScatter({ founders, companies, height = 350 }: FundingScatterProps) {
  const companyMap = new Map(companies.map(c => [c.id, c]))

  const chartData: ScatterPoint[] = founders
    .filter(f => f.age_at_founding && f.domain_exp_years != null)
    .map(f => {
      const company = companyMap.get(f.company_id)
      return {
        x: f.age_at_founding!,
        y: f.domain_exp_years!,
        z: company?.total_raised_usd ? Math.log10(company.total_raised_usd) * 20 : 30,
        name: f.full_name,
        company: company?.name ?? 'Unknown',
        sector: company?.sector ?? 'Unknown',
        color: getSectorColor(company?.sector ?? ''),
      }
    })

  return (
    <div style={{ minHeight: height }}>
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
        <XAxis
          type="number"
          dataKey="x"
          name="Age at Founding"
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
          axisLine={{ stroke: '#1F2937' }}
          tickLine={false}
          label={{ value: 'Age at Founding', position: 'insideBottom', offset: -5, fill: '#4B5563', fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Domain Experience (yrs)"
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          label={{ value: 'Experience (yrs)', angle: -90, position: 'insideLeft', fill: '#4B5563', fontSize: 11 }}
        />
        <ZAxis type="number" dataKey="z" range={[30, 200]} />
        <Tooltip content={<CustomTooltip />} cursor={false} />
        <Scatter data={chartData} fillOpacity={0.7}>
          {/* Using default fill since Cell per-point coloring works */}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
    </div>
  )
}
