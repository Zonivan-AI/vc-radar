'use client'

import { SectorDonut } from '@/components/charts/sector-donut'
import type { SectorStat } from '@/lib/types'

export function SectorBreakdownSection({ data }: { data: SectorStat[] }) {
  return <SectorDonut data={data} height={250} />
}
