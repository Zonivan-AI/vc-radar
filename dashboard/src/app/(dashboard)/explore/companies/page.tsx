'use client'

import { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { FilterBar } from '@/components/ui/filter-bar'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge, ConfidenceBadge, Badge } from '@/components/ui/badge'
import { demoCompanies, demoFounders } from '@/lib/demo-data'

export default function CompanyDatabasePage() {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [stageFilter, setStageFilter] = useState('')

  const companiesWithFounders = demoCompanies.map(c => {
    const founder = demoFounders.find(f => f.company_id === c.id && f.role === 'primary')
    return { ...c, founder }
  })

  const filtered = useMemo(() => {
    return companiesWithFounders.filter(c => {
      if (search) {
        const q = search.toLowerCase()
        if (!c.name.toLowerCase().includes(q) &&
            !c.sector?.toLowerCase().includes(q) &&
            !c.founder?.full_name.toLowerCase().includes(q)) return false
      }
      if (sectorFilter && !c.sector?.toLowerCase().includes(sectorFilter.toLowerCase())) return false
      if (statusFilter && c.status !== statusFilter) return false
      if (stageFilter && c.stage !== stageFilter) return false
      return true
    })
  }, [companiesWithFounders, search, sectorFilter, statusFilter, stageFilter])

  const sectors = [...new Set(demoCompanies.map(c => c.sector).filter(Boolean))]
  const stages = [...new Set(demoCompanies.map(c => c.stage).filter(Boolean))]

  type CompanyRow = typeof filtered[number]

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Portfolio Companies</h1>
        <p className="text-text-secondary mt-2">
          {demoCompanies.length} AI companies tracked across {new Set(demoCompanies.map(c => c.sector)).size} sectors
        </p>
      </div>

      <FilterBar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search companies, sectors, founders..."
        filters={[
          {
            label: 'Stage',
            value: stageFilter,
            onChange: setStageFilter,
            options: stages.map(s => ({ value: s!, label: s! })),
          },
          {
            label: 'Status',
            value: statusFilter,
            onChange: setStatusFilter,
            options: ['Active', 'Acquired', 'IPO', 'Shutdown'].map(s => ({ value: s, label: s })),
          },
        ]}
        className="mb-6"
      />

      <p className="text-sm text-text-muted mb-4">{filtered.length} results</p>

      <DataTable<CompanyRow>
        data={filtered}
        onRowClick={(item) => router.push(`/explore/companies/${item.slug}`)}
        columns={[
          {
            key: 'name',
            header: 'Company',
            render: (item) => (
              <div>
                <div className="font-medium text-text-primary">{item.name}</div>
                <div className="text-xs text-text-muted">{item.sector}</div>
              </div>
            ),
          },
          {
            key: 'founder',
            header: 'Founder',
            render: (item) => item.founder ? (
              <div>
                <div className="text-text-primary">{item.founder.full_name}</div>
                {item.founder.age_at_founding && (
                  <div className="text-xs text-text-muted">Age {item.founder.age_at_founding} at founding</div>
                )}
              </div>
            ) : <span className="text-text-muted">—</span>,
          },
          {
            key: 'stage',
            header: 'Stage',
            render: (item) => item.stage ? <Badge variant="indigo">{item.stage}</Badge> : <span className="text-text-muted">—</span>,
          },
          {
            key: 'status',
            header: 'Status',
            render: (item) => <StatusBadge status={item.status} />,
          },
          {
            key: 'city',
            header: 'Location',
            render: (item) => (
              <span className="text-text-secondary">
                {[item.city, item.country].filter(Boolean).join(', ') || '—'}
              </span>
            ),
          },
          {
            key: 'founded_year',
            header: 'Founded',
            render: (item) => (
              <span className="font-mono text-text-secondary">{item.founded_year ?? '—'}</span>
            ),
            className: 'text-right',
          },
        ]}
        emptyMessage="No companies match your filters."
      />
    </div>
  )
}
