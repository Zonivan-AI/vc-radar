'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { Building2, MapPin, ArrowRight } from 'lucide-react'
import { FilterBar } from '@/components/ui/filter-bar'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { demoVCFirms } from '@/lib/demo-data'
import { getVCsWithCounts } from '@/lib/supabase'
import type { VCFirm } from '@/lib/types'

type VCWithCount = VCFirm & { company_count: number }

export default function VCDirectoryPage() {
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [regionFilter, setRegionFilter] = useState('')

  const [vcList, setVcList] = useState<VCWithCount[]>(
    demoVCFirms.map(f => ({ ...f, company_count: 0 }))
  )

  // Attempt to load live data from Supabase; fall back to demo data on error or
  // empty result.
  useEffect(() => {
    async function loadData() {
      try {
        const data = await getVCsWithCounts()
        if (data.length > 0) {
          // Sort by company_count descending
          data.sort((a, b) => b.company_count - a.company_count)
          setVcList(data)
        }
      } catch {
        // Supabase not configured or unavailable — keep demo data
      }
    }
    loadData()
  }, [])

  const filtered = useMemo(() => {
    return vcList.filter(vc => {
      if (search && !vc.name.toLowerCase().includes(search.toLowerCase())) return false
      if (stageFilter && !vc.fund_stage?.some(s => s.toLowerCase().includes(stageFilter.toLowerCase()))) return false
      if (regionFilter && vc.hq_region !== regionFilter) return false
      return true
    })
  }, [vcList, search, stageFilter, regionFilter])

  const stages = ['Seed', 'Series A', 'Series B', 'Growth']
  const regions = [...new Set(vcList.map(f => f.hq_region).filter(Boolean))]

  const totalCompanies = vcList.reduce((s, v) => s + v.company_count, 0)

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">VC Firms</h1>
        <p className="text-text-secondary mt-2">
          {vcList.length} firms tracking {totalCompanies} companies
        </p>
      </div>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search VC firms..."
        filters={[
          {
            label: 'Stage',
            value: stageFilter,
            onChange: setStageFilter,
            options: stages.map(s => ({ value: s, label: s })),
          },
          {
            label: 'Region',
            value: regionFilter,
            onChange: setRegionFilter,
            options: regions.map(r => ({ value: r!, label: r! })),
          },
        ]}
        className="mb-6"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((vc) => (
          <Link
            key={vc.id}
            href={`/explore/vcs/${vc.slug}`}
            className="glass-card-hover p-5 group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold text-text-primary group-hover:text-accent transition-colors">
                    {vc.name}
                  </h3>
                  {vc.hq_city && (
                    <div className="flex items-center gap-1 text-xs text-text-muted">
                      <MapPin className="w-3 h-3" />
                      {vc.hq_city}
                    </div>
                  )}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-accent transition-colors" />
            </div>

            {vc.fund_stage && vc.fund_stage.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {vc.fund_stage.map(s => (
                  <Badge key={s} variant="accent">{s}</Badge>
                ))}
              </div>
            )}

            <div className="pt-3 border-t border-border/50">
              <div>
                <div className="text-lg font-bold font-mono text-text-primary">{vc.company_count}</div>
                <div className="text-xs text-text-muted">companies</div>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="glass-card p-12 text-center">
          <p className="text-text-muted">No VC firms match your filters.</p>
        </div>
      )}
    </div>
  )
}
