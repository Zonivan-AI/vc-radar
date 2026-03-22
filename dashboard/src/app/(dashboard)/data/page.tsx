import { Download, Github, Code, Database, FileSpreadsheet, FileJson, ExternalLink } from 'lucide-react'
import Link from 'next/link'

export default function DataPage() {
  return (
    <div className="page-container">
      <div className="max-w-4xl mx-auto">
        <div className="mb-10">
          <h1 className="text-3xl font-bold text-text-primary">Data & API</h1>
          <p className="text-text-secondary mt-2">
            Download the full dataset, access the API, or contribute data.
          </p>
        </div>

        {/* Download Section */}
        <div className="glass-card p-6 mb-6">
          <h2 className="section-title mb-1 flex items-center gap-2">
            <Download className="w-5 h-5 text-indigo-light" />
            Download Dataset
          </h2>
          <p className="section-subtitle mb-6">
            Complete dataset of 142 companies, 20 VCs, and 300+ founders. Updated weekly.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <a
              href="/api/export/csv"
              className="p-4 rounded-lg border border-border hover:border-indigo/30 hover:bg-white/[0.02] transition-all group text-center"
            >
              <FileSpreadsheet className="w-8 h-8 text-emerald mx-auto mb-2" />
              <div className="font-medium text-text-primary group-hover:text-indigo-light transition-colors">
                CSV
              </div>
              <div className="text-xs text-text-muted mt-1">Comma-separated values</div>
            </a>

            <a
              href="/api/export/json"
              className="p-4 rounded-lg border border-border hover:border-indigo/30 hover:bg-white/[0.02] transition-all group text-center"
            >
              <FileJson className="w-8 h-8 text-amber mx-auto mb-2" />
              <div className="font-medium text-text-primary group-hover:text-indigo-light transition-colors">
                JSON
              </div>
              <div className="text-xs text-text-muted mt-1">Structured JSON with relations</div>
            </a>

            <a
              href="/api/export/xlsx"
              className="p-4 rounded-lg border border-border hover:border-indigo/30 hover:bg-white/[0.02] transition-all group text-center"
            >
              <FileSpreadsheet className="w-8 h-8 text-indigo-light mx-auto mb-2" />
              <div className="font-medium text-text-primary group-hover:text-indigo-light transition-colors">
                Excel
              </div>
              <div className="text-xs text-text-muted mt-1">Formatted .xlsx with analytics</div>
            </a>
          </div>
        </div>

        {/* API Section */}
        <div className="glass-card p-6 mb-6">
          <h2 className="section-title mb-1 flex items-center gap-2">
            <Code className="w-5 h-5 text-emerald" />
            API Access
          </h2>
          <p className="section-subtitle mb-6">
            Read-only REST API powered by Supabase. No authentication required.
          </p>

          <div className="space-y-3">
            {[
              { method: 'GET', path: '/rest/v1/vc_firms', desc: 'List all VC firms' },
              { method: 'GET', path: '/rest/v1/portfolio_companies', desc: 'List all companies' },
              { method: 'GET', path: '/rest/v1/founders', desc: 'List all founders' },
              { method: 'GET', path: '/rest/v1/mv_vc_stats', desc: 'Aggregated VC statistics' },
              { method: 'GET', path: '/rest/v1/mv_global_stats', desc: 'Global platform stats' },
            ].map(endpoint => (
              <div key={endpoint.path} className="flex items-center gap-3 p-3 rounded-lg bg-surface-raised/50">
                <span className="badge-emerald text-[10px] font-mono">{endpoint.method}</span>
                <code className="text-sm text-indigo-light font-mono flex-1">{endpoint.path}</code>
                <span className="text-xs text-text-muted hidden sm:inline">{endpoint.desc}</span>
              </div>
            ))}
          </div>

          <div className="mt-4 p-3 rounded-lg bg-surface-raised/30 border border-border/50">
            <p className="text-xs text-text-muted">
              Base URL: <code className="text-indigo-light">https://your-project.supabase.co</code>
            </p>
            <p className="text-xs text-text-muted mt-1">
              Add <code className="text-amber">?select=name,sector&order=name</code> for filtering and sorting.
              See <a href="https://supabase.com/docs/reference/javascript" target="_blank" rel="noopener noreferrer" className="text-indigo-light hover:text-indigo">Supabase docs</a> for full API reference.
            </p>
          </div>
        </div>

        {/* Contribute Section */}
        <div className="glass-card p-6 mb-6">
          <h2 className="section-title mb-1 flex items-center gap-2">
            <Github className="w-5 h-5 text-text-primary" />
            Contribute Data
          </h2>
          <p className="section-subtitle mb-6">
            VC Radar is open-source and community-driven. Help us grow the dataset.
          </p>

          <div className="space-y-4">
            <div className="p-4 rounded-lg border border-border/50">
              <h3 className="text-sm font-semibold text-text-primary mb-2">Add a new VC firm</h3>
              <p className="text-xs text-text-secondary mb-3">
                Edit <code className="text-indigo-light">config/vc_list.yaml</code> and submit a PR.
                The pipeline will automatically scrape and process the new VC.
              </p>
              <a
                href="https://github.com/Zonivan-AI/vc-radar/edit/main/config/vc_list.yaml"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-xs py-1.5 gap-1.5"
              >
                Edit on GitHub <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="p-4 rounded-lg border border-border/50">
              <h3 className="text-sm font-semibold text-text-primary mb-2">Correct existing data</h3>
              <p className="text-xs text-text-secondary mb-3">
                Found incorrect founder age, company status, or other data?
                Open an issue or submit a correction PR.
              </p>
              <a
                href="https://github.com/Zonivan-AI/vc-radar/issues/new?template=data-correction.md"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary text-xs py-1.5 gap-1.5"
              >
                Report Issue <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Data Sources */}
        <div className="glass-card p-6">
          <h2 className="section-title mb-1 flex items-center gap-2">
            <Database className="w-5 h-5 text-amber" />
            Data Sources & Methodology
          </h2>
          <div className="mt-4 space-y-3 text-sm text-text-secondary">
            <p>
              All data is sourced from publicly available information. We do not scrape
              LinkedIn or any platform that prohibits automated access.
            </p>
            <p>
              <strong className="text-text-primary">Sources include:</strong> VC firm websites (portfolio pages),
              press releases, SEC EDGAR filings, Wikipedia, public news articles, and
              publicly available biographical information.
            </p>
            <p>
              <strong className="text-text-primary">Age estimation:</strong> Founder ages are estimated using
              publicly available information (education timelines, career history, public interviews).
              Each estimate includes a confidence level (High/Medium/Low) and the inference method used.
            </p>
            <p>
              <strong className="text-text-primary">AI extraction:</strong> We use Claude (Anthropic) for structured
              data extraction from web pages and search results. All AI-extracted data goes through
              validation and quality scoring before entering the database.
            </p>
            <p className="text-text-muted text-xs mt-4">
              If you are a founder and want your data removed or corrected, please{' '}
              <a href="https://github.com/Zonivan-AI/vc-radar/issues" target="_blank" rel="noopener noreferrer" className="text-indigo-light hover:text-indigo">
                open an issue
              </a>{' '}
              on GitHub.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
