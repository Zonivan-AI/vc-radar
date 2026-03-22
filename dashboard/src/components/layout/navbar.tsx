'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import {
  ChevronDown, Menu, X, Github, Download,
  Building2, Briefcase, Users, TrendingUp,
  Compass, Zap, Radio
} from 'lucide-react'

const exploreItems = [
  { href: '/explore/vcs', label: 'VC Firms', icon: Building2, description: 'Browse 20+ VC firms' },
  { href: '/explore/companies', label: 'Portfolio Companies', icon: Briefcase, description: '140+ AI companies' },
  { href: '/explore/founders', label: 'Founder Analytics', icon: Users, description: 'Age, experience, education' },
]

const navItems = [
  { href: '/trends', label: 'Trends' },
  { href: '/match', label: 'Match' },
]

interface NavbarProps {
  variant?: 'default' | 'transparent'
}

export function Navbar({ variant = 'default' }: NavbarProps) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [exploreOpen, setExploreOpen] = useState(false)

  const isTransparent = variant === 'transparent'

  return (
    <nav className={cn(
      'sticky top-0 z-50 border-b',
      isTransparent
        ? 'backdrop-blur-xl border-white/[0.04]'
        : 'bg-background/80 backdrop-blur-xl border-border'
    )}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors" style={{ background: 'rgba(124, 143, 255, 0.12)' }}>
              <Radio className="w-4 h-4" style={{ color: '#7C8FFF' }} />
            </div>
            <span className="text-lg font-bold text-text-primary tracking-tight">
              VC Radar
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {/* Explore Dropdown */}
            <div className="relative"
              onMouseEnter={() => setExploreOpen(true)}
              onMouseLeave={() => setExploreOpen(false)}
            >
              <button className={cn(
                'flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                pathname.startsWith('/explore')
                  ? 'text-indigo-light bg-indigo/10'
                  : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
              )}>
                Explore
                <ChevronDown className={cn('w-4 h-4 transition-transform', exploreOpen && 'rotate-180')} />
              </button>

              {exploreOpen && (
                <div className="absolute top-full left-0 mt-1 w-72 bg-surface-raised border border-border rounded-xl shadow-glass overflow-hidden animate-fade-in">
                  {exploreItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        'flex items-center gap-3 px-4 py-3 transition-colors',
                        pathname === item.href
                          ? 'bg-indigo/10 text-indigo-light'
                          : 'hover:bg-white/5 text-text-secondary hover:text-text-primary'
                      )}
                    >
                      <item.icon className="w-5 h-5" />
                      <div>
                        <div className="text-sm font-medium">{item.label}</div>
                        <div className="text-xs text-text-muted">{item.description}</div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  pathname === item.href
                    ? 'text-indigo-light bg-indigo/10'
                    : 'text-text-secondary hover:text-text-primary hover:bg-white/5'
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="/data" className="btn-secondary text-sm py-1.5 px-3 gap-1.5">
              <Download className="w-3.5 h-3.5" />
              Data
            </Link>
            <a
              href="https://github.com/Zonivan-AI/vc-radar"
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/5 transition-colors"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2 rounded-lg text-text-secondary hover:text-text-primary"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-surface animate-fade-in">
          <div className="px-4 py-4 space-y-1">
            <div className="text-xs font-medium text-text-muted uppercase tracking-wider px-3 py-2">
              Explore
            </div>
            {exploreItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/5"
                onClick={() => setMobileOpen(false)}
              >
                <item.icon className="w-4 h-4" />
                <span className="text-sm">{item.label}</span>
              </Link>
            ))}
            <div className="h-px bg-border my-2" />
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="block px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-white/5"
                onClick={() => setMobileOpen(false)}
              >
                {item.label}
              </Link>
            ))}
            <Link
              href="/data"
              className="block px-3 py-2.5 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-white/5"
              onClick={() => setMobileOpen(false)}
            >
              Data & API
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}
