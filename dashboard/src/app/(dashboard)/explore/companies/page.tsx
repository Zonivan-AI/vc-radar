'use client'

import { useState, useMemo, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { FilterBar } from '@/components/ui/filter-bar'
import { DataTable } from '@/components/ui/data-table'
import { StatusBadge, ConfidenceBadge, Badge } from '@/components/ui/badge'
import { demoCompanies, demoFounders } from '@/lib/demo-data'
import { getCompanies, getFounders } from '@/lib/supabase'
import type { Company, Founder } from '@/lib/types'

const PER_PAGE = 50

export default function CompanyDatabasePage() {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [stageFilter, setStageFilter] = useState('')
  const [page, setPage] = useState(1)
  const [companies, setCompanies] = useState<Company[]>([])
  const [founders, setFounders] = useState<Founder[]>([])
  const [loading, setLoading] = useState(true)
  const [usingDemo, setUsingDemo] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function fetchData() {
      try {
        const [fetchedCompanies, fetchedFounders] = await Promise.all([
          getCompanies(),
          getFounders(),
        ])
        if (!cancelled) {
          if (fetchedCompanies.length > 0) {
            setCompanies(fetchedCompanies)
            setFounders(fetchedFounders)
          } else {
            // Empty result — fall back to demo
            setCompanies(demoCompanies as unknown as Company[])
            setFounders(demoFounders as unknown as Founder[])
            setUsingDemo(true)
          }
        }
      } catch {
        if (!cancelled) {
          setCompanies(demoCompanies as unknown as Company[])
          setFounders(demoFounders as unknown as Founder[])
          setUsingDemo(true)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchData()
    return () => { cancelled = true }
  }, [])

  const companiesWithFounders = useMemo(() => {
    return companies.map(c => {
      const founder = founders.find(f => f.company_id === c.id && f.role === 'primary') ?? null
      return { ...c, founder }
    })
  }, [companies, founders])

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

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1)
  }, [search, sectorFilter, statusFilter, stageFilter])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const paginated = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE)

  const sectors = [...new Set(companies.map(c => c.sector).filter(Boolean))]
  const stages = [...new Set(companies.map(c => c.stage).filter(Boolean))]

  type CompanyRow = typeof paginated[number]

  return (
    <div className="page-container">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary">Portfolio Companies</h1>
        <p className="text-text-secondary mt-2">
          {loading ? 'Loading...' : (
            <>
              {companies.length.toLocaleString()} AI companies tracked across {new Set(companies.map(c => c.sector)).size} sectors
              {usingDemo && <span className="text-text-muted ml-2">(demo data)</span>}
            </>
          )}
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

      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-text-muted">
          {filtered.length.toLocaleString()} results
          {filtered.length > PER_PAGE && (
            <span> &middot; Page {page} of {totalPages}</span>
          )}
        </p>
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-sm rounded-md border border-border bg-surface-primary text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-text-muted tabular-nums">
              {((page - 1) * PER_PAGE + 1).toLocaleString()}–{Math.min(page * PER_PAGE, filtered.length).toLocaleString()} of {filtered.length.toLocaleString()}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 text-sm rounded-md border border-border bg-surface-primary text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-text-muted">
          Loading companies...
        </div>
      ) : (
        <DataTable<CompanyRow>
          data={paginated}
          onRowClick={(item) => router.push(`/explore/companies/${item.slug}`)}
          columns={[
            {
              key: 'name',
              header: 'Company',
              render: (item) => (
                <div>
                  <div className="font-medium text-text-primary">{item.name}</div>
                  <div className="text-xs text-text-muted">{item.sector ?? '—'}</div>
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
              render: (item) => item.stage ? <Badge variant="amber">{item.stage}</Badge> : <span className="text-text-muted">—</span>,
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
      )}

      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm rounded-md border border-border bg-surface-primary text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-text-muted tabular-nums">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1.5 text-sm rounded-md border border-border bg-surface-primary text-text-secondary hover:bg-surface-secondary disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
