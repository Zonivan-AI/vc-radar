'use client'

import { useState } from 'react'
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { TrendChart } from '@/components/charts/trend-chart'
import { StatCard } from '@/components/ui/stat-card'

// Demo trend data
const trendData = [
  { year: 2019, 'AI Infra': 3, 'AI Apps': 2, 'Security': 1, 'Dev Tools': 1, 'Healthcare': 2, 'Robotics': 1 },
  { year: 2020, 'AI Infra': 5, 'AI Apps': 4, 'Security': 2, 'Dev Tools': 2, 'Healthcare': 3, 'Robotics': 2 },
  { year: 2021, 'AI Infra': 8, 'AI Apps': 7, 'Security': 3, 'Dev Tools': 4, 'Healthcare': 3, 'Robotics': 2 },
  { year: 2022, 'AI Infra': 14, 'AI Apps': 10, 'Security': 6, 'Dev Tools': 7, 'Healthcare': 4, 'Robotics': 3 },
  { year: 2023, 'AI Infra': 22, 'AI Apps': 15, 'Security': 10, 'Dev Tools': 9, 'Healthcare': 5, 'Robotics': 4 },
  { year: 2024, 'AI Infra': 28, 'AI Apps': 22, 'Security': 14, 'Dev Tools': 12, 'Healthcare': 7, 'Robotics': 5 },
  { year: 2025, 'AI Infra': 18, 'AI Apps': 18, 'Security': 11, 'Dev Tools': 10, 'Healthcare': 6, 'Robotics': 4 },
]

const sectors = ['AI Infra', 'AI Apps', 'Security', 'Dev Tools', 'Healthcare', 'Robotics']

const emergingSectors = [
  { sector: 'AI Agents', growth: 340, direction: 'up' as const },
  { sector: 'AI Security', growth: 180, direction: 'up' as const },
  { sector: 'AI Infrastructure', growth: 120, direction: 'up' as const },
  { sector: 'AI Applications', growth: 45, direction: 'flat' as const },
  { sector: 'Developer Tools', growth: 30, direction: 'flat' as const },
  { sector: 'Robotics', growth: -12, direction: 'down' as const },
]

export default function TrendsPage() {
  const [activeTab, setActiveTab] = useState<'sectors' | 'stages' | 'geography' | 'founders'>('sectors')

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Investment Trends</h1>
        <p className="text-text-secondary mt-2">
          How AI investment is evolving across sectors, stages, and geographies
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 bg-surface rounded-lg w-fit">
        {(['sectors', 'stages', 'geography', 'founders'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-accent/20 text-accent'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Sector Investment Over Time */}
      <div className="glass-card p-6 mb-6">
        <h2 className="section-title mb-1">Sector Investment Over Time</h2>
        <p className="section-subtitle mb-4">
          Number of new investments by sector per year. Toggle sectors via legend.
        </p>
        <TrendChart data={trendData} sectors={sectors} height={380} />
      </div>

      {/* Emerging vs Declining */}
      <div className="glass-card p-6 mb-6">
        <h2 className="section-title mb-4">Emerging vs. Declining Sectors</h2>
        <p className="section-subtitle mb-6">Ranked by year-over-year investment growth rate</p>

        <div className="space-y-3">
          {emergingSectors.map(({ sector, growth, direction }) => (
            <div key={sector} className="flex items-center gap-4">
              <div className="w-5 flex items-center justify-center">
                {direction === 'up' && <ArrowUpRight className="w-4 h-4 text-emerald" />}
                {direction === 'flat' && <Minus className="w-4 h-4 text-amber" />}
                {direction === 'down' && <ArrowDownRight className="w-4 h-4 text-rose" />}
              </div>
              <span className="text-sm text-text-primary w-40">{sector}</span>
              <span className={`text-sm font-mono w-20 ${
                growth > 0 ? 'text-emerald' : growth < 0 ? 'text-rose' : 'text-amber'
              }`}>
                {growth > 0 ? '+' : ''}{growth}% YoY
              </span>
              <div className="flex-1">
                <div className="h-4 bg-surface-raised rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      growth > 100 ? 'bg-emerald' : growth > 0 ? 'bg-emerald/60' : growth === 0 ? 'bg-amber/40' : 'bg-rose/40'
                    }`}
                    style={{ width: `${Math.min(Math.abs(growth) / 4, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Hottest Sector"
          value="AI Agents"
          subtitle="+340% YoY"
          icon={TrendingUp}
        />
        <StatCard
          label="Most Investments"
          value="AI Infra"
          subtitle="28 in 2024"
        />
        <StatCard
          label="Fastest Growing"
          value="Security"
          subtitle="+180% YoY"
        />
        <StatCard
          label="Total 2024"
          value="88"
          subtitle="investments"
        />
      </div>
    </div>
  )
}
