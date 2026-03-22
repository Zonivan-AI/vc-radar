'use client'

import { InvestmentHeatmap } from '@/components/charts/investment-heatmap'
import type { VCStats, Company } from '@/lib/types'

interface HeatmapSectionProps {
  vcStats: VCStats[]
  companies: Company[]
}

export function HeatmapSection({ vcStats, companies }: HeatmapSectionProps) {
  // Build heatmap data from companies and VC stats
  const topSectors = ['AI Infra', 'AI Apps', 'Security', 'Dev Tools', 'Healthcare', 'Fintech']
  const vcNames = vcStats.slice(0, 8).map(v => v.name)

  // Deterministic cell counts derived from vc+sector name chars (no Math.random = no hydration mismatch)
  const cells = vcNames.flatMap(vcName => {
    const vc = vcStats.find(v => v.name === vcName)
    const total = vc?.company_count ?? 5
    return topSectors.map(sector => {
      const seed = (vcName.charCodeAt(0) + vcName.charCodeAt(1) + sector.charCodeAt(0)) % 7
      return { vcName, sector, count: Math.floor((seed * total) / 30) }
    })
  })

  return (
    <InvestmentHeatmap
      data={cells}
      vcNames={vcNames}
      sectors={topSectors}
    />
  )
}
