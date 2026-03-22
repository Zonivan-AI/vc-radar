'use client'

import { useState, useMemo, useEffect } from 'react'
import Link from 'next/link'
import { Building2, MapPin, ArrowRight } from 'lucide-react'
import { FilterBar } from '@/components/ui/filter-bar'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { demoVCStats, demoVCFirms } from '@/lib/demo-data'
import { getVCStats, getVCFirms } from '@/lib/supabase'
import type { VCStats, VCFirm } from '@/lib/types'

export default function VCDirectoryPage() {
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [regionFilter, setRegionFilter] = useState('')

  const [vcStats, setVcStats] = useState<VCStats[]>(demoVCStats)
  const [vcFirms, setVcFirms] = useState<VCFirm[]>(demoVCFirms)

  // Attempt to load live data from Supabase; fall back to demo data on error or
  // empty result.
  useEffect(() => {
    async function loadData() {
      try {
        const [stats, firms] = await Promise.all([getVCStats(), getVCFirms()])
        if (stats.length > 0) {
          setVcStats(stats)
        }
        if (firms.length > 0) {
          setVcFirms(firms)
        }
      } catch {
        // Supabase not configured or unavailable — keep demo data
      }
    }
    loadData()
  }, [])

  const vcData = vcStats.map(stat => {
    const firm = vcFirms.find(f => f.slug === stat.slug)
    return { ...stat, firm }
  })

  const filtered = useMemo(() => {
    return vcData.filter(vc => {
      if (search && !vc.name.toLowerCase().includes(search.toLowerCase())) return false
      if (stageFilter && !vc.firm?.fund_stage?.some(s => s.toLowerCase().includes(stageFilter.toLowerCase()))) return false
      if (regionFilter && vc.firm?.hq_region !== regionFilter) return false
      return true
    })
  }, [vcData, search, stageFilter, regionFilter])

  const stages = ['Seed', 'Series A', 'Series B', 'Growth']
  const regions = [...new Set(vcFirms.map(f => f.hq_region).filter(Boolean))]

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">VC Firms</h1>
        <p className="text-text-secondary mt-2">
          {vcStats.length} firms tracking {vcStats.reduce((s, v) => s + v.company_count, 0)} companies
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
                <div className="w-10 h-10 rounded-lg bg-indigo/10 flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-indigo-light" />
                </div>
                <div>
                  <h3 className="font-semibold text-text-primary group-hover:text-indigo-light transition-colors">
                    {vc.name}
                  </h3>
                  {vc.firm?.hq_city && (
                    <div className="flex items-center gap-1 text-xs text-text-muted">
                      <MapPin className="w-3 h-3" />
                      {vc.firm.hq_city}
                    </div>
                  )}
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-indigo-light transition-colors" />
            </div>

            {vc.firm?.fund_stage && (
              <div className="flex flex-wrap gap-1.5 mb-3">
                {vc.firm.fund_stage.map(s => (
                  <Badge key={s} variant="indigo">{s}</Badge>
                ))}
              </div>
            )}

            <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border/50">
              <div>
                <div className="text-lg font-bold font-mono text-text-primary">{vc.company_count}</div>
                <div className="text-xs text-text-muted">companies</div>
              </div>
              <div>
                <div className="text-lg font-bold font-mono text-text-primary">
                  {vc.avg_founder_age?.toFixed(0) ?? '—'}
                </div>
                <div className="text-xs text-text-muted">avg age</div>
              </div>
              <div>
                <div className="text-lg font-bold font-mono text-text-primary">{vc.sector_diversity}</div>
                <div className="text-xs text-text-muted">sectors</div>
              </div>
            </div>

            {vc.top_sector && (
              <div className="mt-3 text-xs text-text-secondary">
                Top sector: <span className="text-indigo-light">{vc.top_sector}</span>
              </div>
            )}
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
