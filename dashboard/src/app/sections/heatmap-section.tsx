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

  // Generate demo heatmap cells
  const cells = vcNames.flatMap(vcName => {
    const vc = vcStats.find(v => v.name === vcName)
    return topSectors.map(sector => ({
      vcName,
      sector,
      count: Math.floor(Math.random() * (vc?.company_count ?? 5) / 3),
    }))
  })

  return (
    <InvestmentHeatmap
      data={cells}
      vcNames={vcNames}
      sectors={topSectors}
    />
  )
}
