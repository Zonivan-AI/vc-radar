'use client'

import { use } from 'react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  Building2, ExternalLink, MapPin, Calendar,
  Users, TrendingUp, Briefcase, ArrowLeft
} from 'lucide-react'
import { StatCard } from '@/components/ui/stat-card'
import { Badge, StatusBadge } from '@/components/ui/badge'
import { formatCurrency } from '@/lib/utils'
import { demoVCFirms, demoVCStats, demoCompanies, demoFounders } from '@/lib/demo-data'

export default function VCDeepDivePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const firm = demoVCFirms.find(f => f.slug === slug)
  const stats = demoVCStats.find(s => s.slug === slug)

  if (!firm) return notFound()

  // For demo, show all companies as this VC's portfolio
  const portfolioCompanies = demoCompanies.slice(0, stats?.company_count ?? 5)
  const portfolioFounders = demoFounders.filter(f =>
    portfolioCompanies.some(c => c.id === f.company_id)
  )

  return (
    <div className="page-container">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <Link href="/explore/vcs" className="hover:text-text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          VC Firms
        </Link>
        <span>/</span>
        <span className="text-text-primary">{firm.name}</span>
      </div>

      {/* Header */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-indigo/10 flex items-center justify-center">
              <Building2 className="w-7 h-7 text-indigo-light" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{firm.name}</h1>
              {firm.description && (
                <p className="text-sm text-text-secondary mt-1">{firm.description}</p>
              )}
            </div>
          </div>
          {firm.website && (
            <a
              href={firm.website}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-sm py-1.5 gap-1.5"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Website
            </a>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
          {firm.hq_city && (
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-text-muted" />
              {firm.hq_city}, {firm.hq_country}
            </div>
          )}
          {firm.founded_year && (
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-text-muted" />
              Founded {firm.founded_year}
            </div>
          )}
          {firm.aum_usd && (
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-text-muted" />
              {formatCurrency(firm.aum_usd)} AUM
            </div>
          )}
        </div>

        {firm.fund_stage.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-4">
            {firm.fund_stage.map(s => (
              <Badge key={s} variant="indigo">{s}</Badge>
            ))}
            {firm.focus_sectors.map(s => (
              <Badge key={s}>{s}</Badge>
            ))}
          </div>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <StatCard label="Companies" value={stats.company_count} icon={Briefcase} />
          <StatCard label="Avg Age" value={stats.avg_founder_age?.toFixed(1) ?? '—'} subtitle="at founding" />
          <StatCard label="Median Age" value={stats.median_founder_age?.toFixed(0) ?? '—'} />
          <StatCard label="Founders" value={stats.total_founders_profiled} icon={Users} />
          <StatCard label="Sectors" value={stats.sector_diversity} />
        </div>
      )}

      {/* Portfolio Companies */}
      <div className="glass-card p-6">
        <h2 className="section-title mb-4">Portfolio Companies</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {portfolioCompanies.map((company) => {
            const founder = portfolioFounders.find(f => f.company_id === company.id)
            return (
              <Link
                key={company.id}
                href={`/explore/companies/${company.slug}`}
                className="p-4 rounded-lg border border-border/50 hover:border-indigo/30 hover:bg-white/[0.02] transition-all group"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-medium text-text-primary group-hover:text-indigo-light transition-colors">
                    {company.name}
                  </h3>
                  <StatusBadge status={company.status} />
                </div>
                <p className="text-xs text-text-secondary mb-2">{company.sector}</p>
                <div className="flex items-center gap-3 text-xs text-text-muted">
                  {company.city && <span>{company.city}</span>}
                  {company.founded_year && <span>Est. {company.founded_year}</span>}
                  {company.stage && <Badge variant="indigo">{company.stage}</Badge>}
                </div>
                {founder && (
                  <div className="mt-3 pt-3 border-t border-border/30 text-xs">
                    <span className="text-text-muted">Founder:</span>{' '}
                    <span className="text-text-secondary">{founder.full_name}</span>
                    {founder.age_at_founding && (
                      <span className="text-text-muted"> (age {founder.age_at_founding})</span>
                    )}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}
