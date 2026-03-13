'use client'

import { useState } from 'react'
import { Zap, ArrowRight, Building2, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'
import { demoVCStats, demoVCFirms } from '@/lib/demo-data'

interface MatchResult {
  vcName: string
  slug: string
  score: number
  reason: string
  recentInvestments: string[]
}

export default function MatchPage() {
  const [building, setBuilding] = useState('')
  const [stage, setStage] = useState('')
  const [location, setLocation] = useState('')
  const [background, setBackground] = useState('')
  const [results, setResults] = useState<MatchResult[] | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    // Simulate match results (in production, this calls the matching API)
    setTimeout(() => {
      const mockResults: MatchResult[] = demoVCStats.slice(0, 8).map((vc, i) => ({
        vcName: vc.name,
        slug: vc.slug,
        score: Math.max(50, 97 - i * 7 - Math.floor(Math.random() * 5)),
        reason: `Backed ${vc.company_count} companies in AI. Average founder age ${vc.avg_founder_age?.toFixed(0)}. Strong focus on ${vc.top_sector ?? 'AI'}.`,
        recentInvestments: ['Company A', 'Company B', 'Company C'].slice(0, 2 + Math.floor(Math.random() * 2)),
      }))
      setResults(mockResults)
      setLoading(false)
    }, 1500)
  }

  return (
    <div className="page-container">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo/10 text-indigo-light text-xs font-medium mb-4">
            <Zap className="w-3.5 h-3.5" />
            Beta
          </div>
          <h1 className="text-3xl font-bold text-text-primary">Find Your Best-Fit VCs</h1>
          <p className="text-text-secondary mt-2">
            Based on recent investments, stage, sector, and founder profile
          </p>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="glass-card p-6 mb-8">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                What are you building?
              </label>
              <input
                type="text"
                value={building}
                onChange={(e) => setBuilding(e.target.value)}
                placeholder='e.g. "AI infrastructure for real-time data pipelines"'
                className="input-field"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Stage
              </label>
              <div className="flex flex-wrap gap-2">
                {['Pre-Seed', 'Seed', 'Series A', 'Series B'].map(s => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setStage(s)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      stage === s
                        ? 'bg-indigo text-white'
                        : 'bg-surface border border-border text-text-secondary hover:text-text-primary hover:border-indigo/30'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="City or Country"
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-primary mb-1.5">
                Your background <span className="text-text-muted font-normal">(optional, improves match)</span>
              </label>
              <input
                type="text"
                value={background}
                onChange={(e) => setBackground(e.target.value)}
                placeholder='e.g. "ex-Google ML engineer, 8 years, first-time founder"'
                className="input-field"
              />
            </div>

            <button
              type="submit"
              disabled={loading || !building || !stage}
              className="btn-primary w-full gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <>Find My VCs <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </div>
        </form>

        {/* Results */}
        {results && (
          <div className="space-y-4">
            <h2 className="section-title">
              Top {results.length} VCs for your startup
            </h2>

            {results.map((result, i) => (
              <div key={result.slug} className="glass-card-hover p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-indigo/20 flex items-center justify-center text-sm font-bold text-indigo-light">
                      #{i + 1}
                    </div>
                    <div>
                      <h3 className="font-semibold text-text-primary">{result.vcName}</h3>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-surface-raised rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo to-emerald"
                        style={{ width: `${result.score}%` }}
                      />
                    </div>
                    <span className="text-sm font-mono font-bold text-indigo-light">
                      {result.score}%
                    </span>
                  </div>
                </div>

                <p className="text-sm text-text-secondary mb-3">{result.reason}</p>

                <div className="flex items-center justify-between">
                  <div className="flex gap-1.5">
                    {result.recentInvestments.map(inv => (
                      <Badge key={inv}>{inv}</Badge>
                    ))}
                  </div>
                  <Link
                    href={`/explore/vcs/${result.slug}`}
                    className="text-xs text-indigo-light hover:text-indigo flex items-center gap-1"
                  >
                    View Portfolio <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
