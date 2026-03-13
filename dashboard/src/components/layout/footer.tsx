import Link from 'next/link'
import { Compass, Github, ExternalLink } from 'lucide-react'

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-indigo/20 flex items-center justify-center">
                <Compass className="w-3.5 h-3.5 text-indigo-light" />
              </div>
              <span className="text-base font-bold text-text-primary">Meridian</span>
            </div>
            <p className="text-sm text-text-secondary leading-relaxed">
              Open-source VC intelligence for founders, researchers, and operators.
            </p>
          </div>

          {/* Explore */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Explore</h3>
            <ul className="space-y-2">
              <li><Link href="/explore/vcs" className="text-sm text-text-secondary hover:text-text-primary transition-colors">VC Firms</Link></li>
              <li><Link href="/explore/companies" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Companies</Link></li>
              <li><Link href="/explore/founders" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Founder Analytics</Link></li>
              <li><Link href="/trends" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Trends</Link></li>
            </ul>
          </div>

          {/* Data */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Data</h3>
            <ul className="space-y-2">
              <li><Link href="/data" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Download CSV</Link></li>
              <li><Link href="/data" className="text-sm text-text-secondary hover:text-text-primary transition-colors">API Docs</Link></li>
              <li><Link href="/data" className="text-sm text-text-secondary hover:text-text-primary transition-colors">Contribute Data</Link></li>
              <li><Link href="/match" className="text-sm text-text-secondary hover:text-text-primary transition-colors">VC Match</Link></li>
            </ul>
          </div>

          {/* Open Source */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Open Source</h3>
            <ul className="space-y-2">
              <li>
                <a href="https://github.com/Zonivan-AI/vc-radar" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors">
                  <Github className="w-3.5 h-3.5" /> GitHub
                </a>
              </li>
              <li>
                <a href="https://github.com/Zonivan-AI/vc-radar/blob/main/CONTRIBUTING.md" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary transition-colors">
                  <ExternalLink className="w-3.5 h-3.5" /> Contributing
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-text-muted">
            Built for founders, by founders. Open-source forever. MIT License.
          </p>
          <p className="text-xs text-text-muted">
            Data sourced from public information only. Last updated March 2026.
          </p>
        </div>
      </div>
    </footer>
  )
}
