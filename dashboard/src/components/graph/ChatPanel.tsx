'use client'

import { useState, useCallback } from 'react'
import { Search, ChevronLeft, ChevronRight, Building2, Briefcase } from 'lucide-react'
import { motion } from 'framer-motion'
import type { GraphNode, GraphFilters } from '@/lib/graph-types'

interface ChatPanelProps {
  nodes: GraphNode[]
  filters: GraphFilters
  onFiltersChange: (filters: GraphFilters) => void
  onNavigateToNode: (nodeId: string) => void
  vcCount: number
  companyCount: number
}

export function ChatPanel({ nodes, filters, onFiltersChange, onNavigateToNode, vcCount, companyCount }: ChatPanelProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query)
    onFiltersChange({ ...filters, searchQuery: query })
  }, [filters, onFiltersChange])

  const toggleFilter = useCallback((key: 'showVCs' | 'showCompanies') => {
    onFiltersChange({ ...filters, [key]: !filters[key] })
  }, [filters, onFiltersChange])

  // Filter nodes for search results
  const searchResults = searchQuery.length >= 2
    ? nodes.filter(n =>
        n.name.toLowerCase().includes(searchQuery.toLowerCase())
      ).slice(0, 8)
    : []

  const vcResults = searchResults.filter(n => n.type === 'vc')
  const companyResults = searchResults.filter(n => n.type === 'company')

  if (collapsed) {
    return (
      <div
        className="fixed left-4 top-20 z-40 glass-panel flex flex-col items-center py-4 gap-3"
        style={{ width: '52px', height: 'calc(100vh - 96px)' }}
      >
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg text-[#64748B] hover:text-[#E2E8F0] transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg text-[#64748B] hover:text-[#E2E8F0] transition-colors"
        >
          <Search className="w-4 h-4" />
        </button>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ x: -380, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', damping: 30, stiffness: 400 }}
      className="fixed left-4 top-20 z-40 glass-panel flex flex-col overflow-hidden"
      style={{ width: '360px', height: 'calc(100vh - 96px)' }}
    >
      {/* Search */}
      <div className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#475569]" />
          <input
            type="text"
            placeholder="Search the universe..."
            value={searchQuery}
            onChange={e => handleSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm text-[#E2E8F0] placeholder:text-[#475569] transition-all focus:outline-none"
            style={{
              background: 'rgba(15, 23, 42, 0.5)',
              border: '1px solid rgba(148, 163, 184, 0.06)',
            }}
            onFocus={e => {
              e.target.style.boxShadow = '0 0 0 3px rgba(124, 143, 255, 0.12), 0 0 16px rgba(124, 143, 255, 0.08)'
              e.target.style.borderColor = 'rgba(124, 143, 255, 0.2)'
            }}
            onBlur={e => {
              e.target.style.boxShadow = 'none'
              e.target.style.borderColor = 'rgba(148, 163, 184, 0.06)'
            }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {searchQuery.length >= 2 ? (
          /* Search Results */
          <div className="space-y-4">
            {searchResults.length === 0 ? (
              <p className="text-sm text-[#475569] text-center py-8">
                No matches found
              </p>
            ) : (
              <>
                {vcResults.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">VC Firms</p>
                    <div className="space-y-1">
                      {vcResults.map(node => (
                        <button
                          key={node.id}
                          onClick={() => onNavigateToNode(node.id)}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.04] transition-colors text-left"
                        >
                          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#7C8FFF' }} />
                          <span className="text-sm text-[#E2E8F0]">{node.name}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {companyResults.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">Companies</p>
                    <div className="space-y-1">
                      {companyResults.map(node => (
                        <button
                          key={node.id}
                          onClick={() => onNavigateToNode(node.id)}
                          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.04] transition-colors text-left"
                        >
                          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: '#38BDF8' }} />
                          <div>
                            <div className="text-sm text-[#E2E8F0]">{node.name}</div>
                            <div className="text-[11px] text-[#475569]">
                              {(node.data as any).sector ?? ''}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <p className="text-[10px] text-[#334155] text-center pt-2">
                  Press Enter to fly to result
                </p>
              </>
            )}
          </div>
        ) : (
          /* Default: Filters + Stats */
          <div className="space-y-6">
            {/* Filters */}
            <div>
              <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-3">Filters</p>
              <div className="space-y-1.5">
                <button
                  onClick={() => toggleFilter('showVCs')}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center"
                      style={{
                        borderColor: filters.showVCs ? '#7C8FFF' : '#334155',
                        backgroundColor: filters.showVCs ? '#7C8FFF' : 'transparent',
                      }}
                    >
                      {filters.showVCs && (
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                      )}
                    </span>
                    <Building2 className="w-3.5 h-3.5 text-[#64748B]" />
                    <span className="text-sm text-[#94A3B8]">VC Firms</span>
                  </div>
                  <span className="text-xs text-[#475569] font-mono">{vcCount}</span>
                </button>
                <button
                  onClick={() => toggleFilter('showCompanies')}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center"
                      style={{
                        borderColor: filters.showCompanies ? '#38BDF8' : '#334155',
                        backgroundColor: filters.showCompanies ? '#38BDF8' : 'transparent',
                      }}
                    >
                      {filters.showCompanies && (
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                      )}
                    </span>
                    <Briefcase className="w-3.5 h-3.5 text-[#64748B]" />
                    <span className="text-sm text-[#94A3B8]">Companies</span>
                  </div>
                  <span className="text-xs text-[#475569] font-mono">{companyCount}</span>
                </button>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(148,163,184,0.08), transparent)' }} />

            {/* Quick Stats */}
            <div>
              <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-3">Overview</p>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center">
                  <div className="text-lg font-semibold text-[#E2E8F0]">{vcCount}</div>
                  <div className="text-[10px] text-[#475569]">VCs</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-[#E2E8F0]">{companyCount}</div>
                  <div className="text-[10px] text-[#475569]">Companies</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-semibold text-[#E2E8F0]">—</div>
                  <div className="text-[10px] text-[#475569]">Articles</div>
                </div>
              </div>
            </div>

            {/* Divider */}
            <div className="h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(148,163,184,0.08), transparent)' }} />

            {/* Hint */}
            <p className="text-xs text-[#334155] text-center">
              Search or click nodes to explore
            </p>
          </div>
        )}
      </div>

      {/* Collapse button */}
      <div className="px-4 py-3" style={{ borderTop: '1px solid rgba(148, 163, 184, 0.05)' }}>
        <button
          onClick={() => setCollapsed(true)}
          className="flex items-center gap-1.5 text-[11px] text-[#475569] hover:text-[#94A3B8] transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          Collapse
        </button>
      </div>
    </motion.div>
  )
}
