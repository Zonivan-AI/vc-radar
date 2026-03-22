'use client'

import { use } from 'react'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  Briefcase, ExternalLink, MapPin, Calendar,
  User, GraduationCap, ArrowLeft, Shield
} from 'lucide-react'
import { Badge, StatusBadge, ConfidenceBadge } from '@/components/ui/badge'
import { formatCurrency } from '@/lib/utils'
import { demoCompanies, demoFounders, demoVCFirms } from '@/lib/demo-data'

export default function CompanyProfilePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params)
  const company = demoCompanies.find(c => c.slug === slug)

  if (!company) return notFound()

  const founders = demoFounders.filter(f => f.company_id === company.id)
  const primaryFounder = founders.find(f => f.role === 'primary')
  const coFounders = founders.filter(f => f.role === 'co-founder')

  // For demo, pick a VC that "invested" in this company
  const investorVC = demoVCFirms[0]

  return (
    <div className="page-container">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <Link href="/explore/companies" className="hover:text-text-primary transition-colors flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          Companies
        </Link>
        <span>/</span>
        <span className="text-text-primary">{company.name}</span>
      </div>

      {/* Company Header */}
      <div className="glass-card p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-emerald/10 flex items-center justify-center">
              <Briefcase className="w-7 h-7 text-emerald" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text-primary">{company.name}</h1>
              <p className="text-sm text-text-secondary mt-1">{company.sector}</p>
            </div>
          </div>
          <StatusBadge status={company.status} />
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary">
          {company.city && (
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-text-muted" />
              {company.city}, {company.country}
            </div>
          )}
          {company.founded_year && (
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-text-muted" />
              Founded {company.founded_year}
            </div>
          )}
          {company.stage && <Badge variant="indigo">{company.stage}</Badge>}
          {company.total_raised_usd && (
            <span className="font-mono text-emerald">
              {formatCurrency(company.total_raised_usd)} raised
            </span>
          )}
        </div>

        {company.status_detail && (
          <p className="mt-3 text-sm text-amber">{company.status_detail}</p>
        )}

        {/* Investor */}
        <div className="mt-4 pt-4 border-t border-border/50">
          <span className="text-xs text-text-muted">Investor: </span>
          <Link
            href={`/explore/vcs/${investorVC.slug}`}
            className="text-sm text-indigo-light hover:text-indigo transition-colors"
          >
            {investorVC.name}
          </Link>
        </div>
      </div>

      {/* Founder Profile */}
      {primaryFounder && (
        <div className="glass-card p-6 mb-6">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <User className="w-5 h-5 text-indigo-light" />
            Founder Profile
          </h2>

          <div className="space-y-4">
            {/* Primary Founder */}
            <div className="p-4 rounded-lg border border-border/50 bg-surface-raised/50">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-text-primary">{primaryFounder.full_name}</h3>
                  <span className="text-xs text-text-muted">Primary Founder</span>
                </div>
                <ConfidenceBadge confidence={primaryFounder.age_confidence} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {primaryFounder.est_birth_year && (
                  <div>
                    <div className="text-text-muted text-xs">Est. Birth Year</div>
                    <div className="font-mono text-text-primary">~{primaryFounder.est_birth_year}</div>
                  </div>
                )}
                {primaryFounder.age_at_founding && (
                  <div>
                    <div className="text-text-muted text-xs">Age at Founding</div>
                    <div className="font-mono text-text-primary text-lg font-bold">{primaryFounder.age_at_founding}</div>
                  </div>
                )}
                {primaryFounder.domain_exp_years != null && (
                  <div>
                    <div className="text-text-muted text-xs">Domain Experience</div>
                    <div className="font-mono text-text-primary">{primaryFounder.domain_exp_years} years</div>
                  </div>
                )}
                <div>
                  <div className="text-text-muted text-xs">Prior Founder</div>
                  <div className={primaryFounder.prior_founder ? 'text-emerald' : 'text-text-secondary'}>
                    {primaryFounder.prior_founder ? 'Yes' : 'No'}
                  </div>
                </div>
              </div>

              {(primaryFounder.education_tier || primaryFounder.university) && (
                <div className="mt-3 flex items-center gap-2 text-sm">
                  <GraduationCap className="w-4 h-4 text-text-muted" />
                  {primaryFounder.education_tier && (
                    <Badge variant={primaryFounder.education_tier === 'Top-10' ? 'indigo' : 'default'}>
                      {primaryFounder.education_tier}
                    </Badge>
                  )}
                  {primaryFounder.university && (
                    <span className="text-text-secondary">{primaryFounder.university}</span>
                  )}
                </div>
              )}

              {primaryFounder.age_inference_method && (
                <div className="mt-3 flex items-center gap-2 text-xs text-text-muted">
                  <Shield className="w-3.5 h-3.5" />
                  Method: {primaryFounder.age_inference_method}
                </div>
              )}
            </div>

            {/* Co-founders */}
            {coFounders.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-text-secondary mb-2">Co-Founders</h4>
                <div className="flex flex-wrap gap-2">
                  {coFounders.map(f => (
                    <span key={f.id} className="badge bg-white/5 text-text-secondary">
                      {f.full_name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Similar Companies */}
      <div className="glass-card p-6">
        <h2 className="section-title mb-4">Similar Companies</h2>
        <div className="flex flex-wrap gap-3">
          {demoCompanies
            .filter(c => c.id !== company.id && c.sector === company.sector)
            .slice(0, 5)
            .map(c => (
              <Link
                key={c.id}
                href={`/explore/companies/${c.slug}`}
                className="badge-indigo hover:bg-indigo/20 transition-colors"
              >
                {c.name}
              </Link>
            ))}
          {demoCompanies.filter(c => c.id !== company.id && c.sector === company.sector).length === 0 && (
            <span className="text-sm text-text-muted">No similar companies found in this sector.</span>
          )}
        </div>
      </div>
    </div>
  )
}
