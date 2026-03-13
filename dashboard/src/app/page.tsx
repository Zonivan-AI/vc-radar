import Link from 'next/link'
import { ArrowRight, Building2, Briefcase, Users, TrendingUp, Compass } from 'lucide-react'
import { StatCard } from '@/components/ui/stat-card'
import { AgeHistogramSection } from './sections/age-histogram-section'
import { SectorBreakdownSection } from './sections/sector-breakdown-section'
import { HeatmapSection } from './sections/heatmap-section'
import {
  demoGlobalStats, demoAgeBuckets, demoSectorStats,
  demoVCStats, demoCompanies,
} from '@/lib/demo-data'

export default function HomePage() {
  const stats = demoGlobalStats
  const ageBuckets = demoAgeBuckets
  const sectorStats = demoSectorStats
  const vcStats = demoVCStats
  const companies = demoCompanies

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-radial from-indigo/5 via-transparent to-transparent" />
        <div className="page-container relative">
          <div className="max-w-3xl mx-auto text-center py-16 sm:py-24">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo/10 text-indigo-light text-xs font-medium mb-6">
              <Compass className="w-3.5 h-3.5" />
              Open-Source VC Intelligence
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-text-primary leading-tight tracking-tight">
              Navigate the AI{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo to-indigo-light">
                Investment Landscape
              </span>
            </h1>
            <p className="mt-6 text-lg text-text-secondary leading-relaxed max-w-2xl mx-auto">
              Open-source intelligence on {stats.total_companies}+ VC-backed AI companies,{' '}
              {stats.total_vcs} top VC firms, and the founders they back.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/explore/vcs" className="btn-primary gap-2">
                Explore VCs <ArrowRight className="w-4 h-4" />
              </Link>
              <Link href="/match" className="btn-secondary gap-2">
                Find Your VC Match <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="page-container -mt-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="VC Firms" value={stats.total_vcs} icon={Building2} />
          <StatCard label="Companies" value={`${stats.total_companies}+`} subtitle="tracked" icon={Briefcase} />
          <StatCard label="Founders" value={stats.total_founders} subtitle="profiled" icon={Users} />
          <StatCard
            label="Median Age"
            value={stats.median_founder_age ?? 'N/A'}
            subtitle="at founding"
            icon={TrendingUp}
          />
        </div>
      </section>

      {/* Featured Chart: Age Distribution */}
      <section className="page-container">
        <div className="glass-card p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="section-title">Founder Age at Founding</h2>
              <p className="section-subtitle mt-1">
                Distribution across {stats.total_founders} VC-backed AI founders
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="text-text-muted">Median:</span>
                <span className="font-mono font-semibold text-indigo-light">{stats.median_founder_age}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-text-muted">Mean:</span>
                <span className="font-mono font-semibold text-text-primary">{stats.avg_founder_age}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-text-muted">Range:</span>
                <span className="font-mono text-text-secondary">
                  {stats.youngest_founder_age}–{stats.oldest_founder_age}
                </span>
              </div>
            </div>
          </div>
          <AgeHistogramSection data={ageBuckets} />
        </div>
      </section>

      {/* Sector Breakdown + Heatmap */}
      <section className="page-container">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <h2 className="section-title mb-1">Sector Breakdown</h2>
            <p className="section-subtitle mb-4">Investment distribution by sector</p>
            <SectorBreakdownSection data={sectorStats} />
          </div>
          <div className="glass-card p-6">
            <h2 className="section-title mb-1">VC Investment Heatmap</h2>
            <p className="section-subtitle mb-4">Who invests in what</p>
            <HeatmapSection vcStats={vcStats} companies={companies} />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="page-container pb-16">
        <div className="glass-card p-8 text-center">
          <h2 className="text-2xl font-bold text-text-primary mb-3">
            Built for founders, by founders
          </h2>
          <p className="text-text-secondary mb-6 max-w-lg mx-auto">
            Meridian is open-source and community-driven. Help us expand the dataset
            by contributing VCs, companies, or corrections.
          </p>
          <div className="flex items-center justify-center gap-4">
            <a
              href="https://github.com/Zonivan-AI/vc-radar"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-primary gap-2"
            >
              Contribute on GitHub <ArrowRight className="w-4 h-4" />
            </a>
            <Link href="/data" className="btn-secondary">
              Download Data
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
