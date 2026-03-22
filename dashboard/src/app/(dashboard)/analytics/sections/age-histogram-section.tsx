'use client'

import { AgeHistogram } from '@/components/charts/age-histogram'
import type { AgeBucket } from '@/lib/types'

export function AgeHistogramSection({ data }: { data: AgeBucket[] }) {
  return <AgeHistogram data={data} height={300} />
}
