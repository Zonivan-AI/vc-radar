'use client'

import { useState } from 'react'
import { Users, TrendingUp, GraduationCap, Repeat } from 'lucide-react'
import { StatCard } from '@/components/ui/stat-card'
import { AgeHistogram } from '@/components/charts/age-histogram'
import { FundingScatter } from '@/components/charts/funding-scatter'
import {
  demoGlobalStats, demoAgeBuckets, demoFounders,
  demoCompanies, demoVCFirms,
} from '@/lib/demo-data'

export default function FounderAnalyticsPage() {
  const stats = demoGlobalStats
  const founders = demoFounders
  const primaryFounders = founders.filter(f => f.role === 'primary')

  // Education tier breakdown
  const educationBreakdown = primaryFounders.reduce<Record<string, number>>((acc, f) => {
    const tier = f.education_tier ?? 'Unknown'
    acc[tier] = (acc[tier] || 0) + 1
    return acc
  }, {})

  // Prior founder rate
  const priorFounderCount = primaryFounders.filter(f => f.prior_founder).length
  const priorFounderPct = primaryFounders.length > 0
    ? Math.round((priorFounderCount / primaryFounders.length) * 100)
    : 0

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Founder Analytics</h1>
        <p className="text-text-secondary mt-2">
          How old, how experienced, how educated are the founders VCs back?
        </p>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Founders Profiled" value={stats.total_founders} icon={Users} />
        <StatCard label="Median Age" value={stats.median_founder_age ?? '—'} subtitle="at founding" icon={TrendingUp} />
        <StatCard label="Age Range" value={`${stats.youngest_founder_age}–${stats.oldest_founder_age}`} />
        <StatCard label="Prior Founders" value={`${priorFounderPct}%`} icon={Repeat} />
      </div>

      {/* Age Distribution */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="section-title">Age at Founding Distribution</h2>
            <p className="section-subtitle mt-1">
              Interactive histogram across {primaryFounders.length} primary founders
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs">
            <div>
              <span className="text-text-muted">Median: </span>
              <span className="font-mono font-semibold text-accent">{stats.median_founder_age}</span>
            </div>
            <div>
              <span className="text-text-muted">Mean: </span>
              <span className="font-mono font-semibold text-text-primary">{stats.avg_founder_age}</span>
            </div>
          </div>
        </div>
        <AgeHistogram data={demoAgeBuckets} height={320} />
      </div>

      {/* Experience vs Funding Scatter */}
      <div className="glass-card p-6 mb-6">
        <h2 className="section-title mb-1">Experience vs. Age at Founding</h2>
        <p className="section-subtitle mb-4">
          Domain experience (years) plotted against founder age. Hover for details.
        </p>
        <FundingScatter founders={founders} companies={demoCompanies} height={380} />
      </div>

      {/* Bottom row: Education + Prior Founder */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Education Tier */}
        <div className="glass-card p-6">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-accent" />
            Education Tier Breakdown
          </h2>
          <div className="space-y-3">
            {Object.entries(educationBreakdown)
              .sort(([, a], [, b]) => b - a)
              .map(([tier, count]) => {
                const pct = Math.round((count / primaryFounders.length) * 100)
                return (
                  <div key={tier}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-text-secondary">{tier}</span>
                      <span className="font-mono text-text-primary">{pct}%</span>
                    </div>
                    <div className="w-full h-2 bg-surface-raised rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-accent transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                )
              })}
          </div>
        </div>

        {/* Prior Founder Rate */}
        <div className="glass-card p-6">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <Repeat className="w-5 h-5 text-emerald" />
            Prior Founder Rate
          </h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-text-secondary">First-time Founders</span>
                <span className="font-mono text-text-primary">{100 - priorFounderPct}%</span>
              </div>
              <div className="w-full h-3 bg-surface-raised rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent"
                  style={{ width: `${100 - priorFounderPct}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-text-secondary">Serial Founders</span>
                <span className="font-mono text-emerald">{priorFounderPct}%</span>
              </div>
              <div className="w-full h-3 bg-surface-raised rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-emerald"
                  style={{ width: `${priorFounderPct}%` }}
                />
              </div>
            </div>

            <div className="pt-4 border-t border-border/50">
              <p className="text-xs text-text-muted">
                {priorFounderPct}% of VC-backed AI founders had previously founded a company.
                Serial founders tend to be older (avg 35) vs first-time (avg 28).
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
