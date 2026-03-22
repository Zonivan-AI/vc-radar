'use client'

import { useState } from 'react'
import { X, ArrowRight } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import type { GraphNode } from '@/lib/graph-types'
import type { VCFirm, Company } from '@/lib/types'
import { formatCurrency } from '@/lib/utils'

interface NodeDetailPanelProps {
  node: GraphNode | null
  onClose: () => void
  onNavigateToNode: (nodeId: string) => void
  connectedNodes: GraphNode[]
}

function VCDetail({
  vc,
  connectedNodes,
  onNavigateToNode,
}: {
  vc: VCFirm
  connectedNodes: GraphNode[]
  onNavigateToNode: (id: string) => void
}) {
  const portfolioNodes = connectedNodes.filter(n => n.type === 'company')
  const [showAll, setShowAll] = useState(false)
  const displayNodes = showAll ? portfolioNodes : portfolioNodes.slice(0, 5)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: '#7C8FFF' }} />
          <span className="text-[11px] text-[#7C8FFF]">VC Firm</span>
        </div>
        <h2 className="text-xl font-bold text-[#E2E8F0]">{vc.name}</h2>
        {vc.hq_city && (
          <p className="text-sm text-[#64748B] mt-0.5">{vc.hq_city}, {vc.hq_country}</p>
        )}
      </div>

      {/* Divider */}
      <div className="h-px" style={{ background: 'linear-gradient(to right, rgba(148,163,184,0.08), transparent)' }} />

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4">
        {vc.aum_usd && (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{formatCurrency(vc.aum_usd)}</div>
            <div className="text-[10px] text-[#475569] uppercase">AUM</div>
          </div>
        )}
        {vc.founded_year && (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{vc.founded_year}</div>
            <div className="text-[10px] text-[#475569] uppercase">Founded</div>
          </div>
        )}
        <div>
          <div className="text-base font-semibold text-[#E2E8F0]">{portfolioNodes.length}</div>
          <div className="text-[10px] text-[#475569] uppercase">Companies</div>
        </div>
      </div>

      {/* Stages */}
      {vc.fund_stage?.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">Stages</p>
          <div className="flex flex-wrap gap-1.5">
            {vc.fund_stage.map(stage => (
              <span
                key={stage}
                className="text-[11px] px-2.5 py-1 rounded-full text-[#7C8FFF]"
                style={{ background: 'rgba(124, 143, 255, 0.08)', border: '1px solid rgba(124, 143, 255, 0.12)' }}
              >
                {stage}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Portfolio */}
      {portfolioNodes.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">Portfolio</p>
          <div className="space-y-0.5">
            {displayNodes.map(node => (
              <button
                key={node.id}
                onClick={() => onNavigateToNode(node.id)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/[0.03] transition-colors text-left"
              >
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#38BDF8' }} />
                <span className="text-sm text-[#94A3B8] hover:text-[#E2E8F0] transition-colors">
                  {node.name}
                </span>
              </button>
            ))}
            {!showAll && portfolioNodes.length > 5 && (
              <button
                onClick={() => setShowAll(true)}
                className="text-[11px] text-[#7C8FFF] hover:text-[#A5B4FC] px-3 py-1.5 transition-colors"
              >
                + {portfolioNodes.length - 5} more
              </button>
            )}
          </div>
        </div>
      )}

      {/* CTA */}
      <Link
        href={`/explore/vcs/${vc.slug}`}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium text-[#7C8FFF] transition-colors hover:text-[#A5B4FC]"
        style={{ background: 'rgba(124, 143, 255, 0.06)', border: '1px solid rgba(124, 143, 255, 0.10)' }}
      >
        View Profile <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  )
}

function CompanyDetail({
  company,
  connectedNodes,
  onNavigateToNode,
}: {
  company: Company
  connectedNodes: GraphNode[]
  onNavigateToNode: (id: string) => void
}) {
  const investorNodes = connectedNodes.filter(n => n.type === 'vc')

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: '#38BDF8' }} />
          <span className="text-[11px] text-[#38BDF8]">Company</span>
        </div>
        <h2 className="text-xl font-bold text-[#E2E8F0]">{company.name}</h2>
        {company.sector && (
          <p className="text-sm text-[#64748B] mt-0.5">{company.sector}</p>
        )}
      </div>

      {/* Divider */}
      <div className="h-px" style={{ background: 'linear-gradient(to right, rgba(148,163,184,0.08), transparent)' }} />

      {/* Metrics Grid */}
      <div className="grid grid-cols-3 gap-4">
        {company.stage && (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{company.stage}</div>
            <div className="text-[10px] text-[#475569] uppercase">Stage</div>
          </div>
        )}
        {company.founded_year && (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{company.founded_year}</div>
            <div className="text-[10px] text-[#475569] uppercase">Founded</div>
          </div>
        )}
        {company.total_raised_usd ? (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{formatCurrency(company.total_raised_usd)}</div>
            <div className="text-[10px] text-[#475569] uppercase">Raised</div>
          </div>
        ) : (
          <div>
            <div className="text-base font-semibold text-[#E2E8F0]">{company.status}</div>
            <div className="text-[10px] text-[#475569] uppercase">Status</div>
          </div>
        )}
      </div>

      {company.city && (
        <p className="text-xs text-[#64748B]">{company.city}, {company.country}</p>
      )}

      {/* Investors */}
      {investorNodes.length > 0 && (
        <div>
          <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">Investors</p>
          <div className="space-y-0.5">
            {investorNodes.map(node => (
              <button
                key={node.id}
                onClick={() => onNavigateToNode(node.id)}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-white/[0.03] transition-colors text-left"
              >
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: '#7C8FFF' }} />
                <span className="text-sm text-[#94A3B8] hover:text-[#E2E8F0] transition-colors">
                  {node.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* CTA */}
      <Link
        href={`/explore/companies/${company.slug}`}
        className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-medium text-[#38BDF8] transition-colors hover:text-[#67E8F9]"
        style={{ background: 'rgba(56, 189, 248, 0.06)', border: '1px solid rgba(56, 189, 248, 0.10)' }}
      >
        View Profile <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  )
}

export function NodeDetailPanel({ node, onClose, onNavigateToNode, connectedNodes }: NodeDetailPanelProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: 'spring', damping: 30, stiffness: 400 }}
          className="fixed right-4 top-20 z-40 glass-panel overflow-y-auto"
          style={{ width: '380px', height: 'calc(100vh - 96px)' }}
        >
          <div className="p-5">
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-[#475569] hover:text-[#E2E8F0] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {node.type === 'vc' ? (
              <VCDetail
                vc={node.data as VCFirm}
                connectedNodes={connectedNodes}
                onNavigateToNode={onNavigateToNode}
              />
            ) : (
              <CompanyDetail
                company={node.data as Company}
                connectedNodes={connectedNodes}
                onNavigateToNode={onNavigateToNode}
              />
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
