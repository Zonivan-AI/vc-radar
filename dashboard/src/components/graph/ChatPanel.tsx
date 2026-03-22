'use client'

import {
  useState, useCallback, useRef, useEffect, useMemo,
} from 'react'
import {
  Search, ChevronLeft, ChevronRight, Send,
  Building2, Briefcase, TrendingUp, Calendar, Zap,
  Sparkles, BarChart3, Globe,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { GraphNode, GraphFilters } from '@/lib/graph-types'
import type { VCFirm, Company, Investment } from '@/lib/types'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  action?: SlashAction
  nodeResults?: GraphNode[]
}

interface SlashAction {
  command: string
  label: string
  icon: React.ReactNode
  description: string
  example?: string
}

interface ChatPanelProps {
  nodes: GraphNode[]
  filters: GraphFilters
  onFiltersChange: (filters: GraphFilters) => void
  onNavigateToNode: (nodeId: string) => void
  vcCount: number
  companyCount: number
  vcs: VCFirm[]
  companies: Company[]
  investments: Investment[]
}

// ---------------------------------------------------------------------------
// Slash actions registry
// ---------------------------------------------------------------------------

const SLASH_ACTIONS: SlashAction[] = [
  {
    command: '/search',
    label: 'Search',
    icon: <Search className="w-3.5 h-3.5" />,
    description: 'Search VCs and companies',
    example: '/search Perplexity',
  },
  {
    command: '/vc',
    label: 'VC Lookup',
    icon: <Building2 className="w-3.5 h-3.5" />,
    description: 'Look up a specific VC firm',
    example: '/vc Khosla',
  },
  {
    command: '/company',
    label: 'Company',
    icon: <Briefcase className="w-3.5 h-3.5" />,
    description: 'Look up a specific company',
    example: '/company ElevenLabs',
  },
  {
    command: '/weekly',
    label: 'This Week',
    icon: <Calendar className="w-3.5 h-3.5" />,
    description: 'What happened this week',
  },
  {
    command: '/latest',
    label: 'Latest',
    icon: <TrendingUp className="w-3.5 h-3.5" />,
    description: 'Latest funding rounds & deals',
  },
  {
    command: '/stats',
    label: 'Stats',
    icon: <BarChart3 className="w-3.5 h-3.5" />,
    description: 'Overview statistics',
  },
  {
    command: '/sectors',
    label: 'Sectors',
    icon: <Globe className="w-3.5 h-3.5" />,
    description: 'Sector breakdown',
  },
  {
    command: '/hot',
    label: 'Hot Deals',
    icon: <Zap className="w-3.5 h-3.5" />,
    description: 'Most active VCs and trending companies',
  },
]

// ---------------------------------------------------------------------------
// Typewriter bubble
// ---------------------------------------------------------------------------

function TypewriterText({ text, onDone }: { text: string; onDone?: () => void }) {
  const [displayed, setDisplayed] = useState('')
  const idx = useRef(0)

  useEffect(() => {
    idx.current = 0
    setDisplayed('')
    if (!text) { onDone?.(); return }

    const timer = setInterval(() => {
      idx.current++
      setDisplayed(text.slice(0, idx.current))
      if (idx.current >= text.length) {
        clearInterval(timer)
        onDone?.()
      }
    }, 14)
    return () => clearInterval(timer)
  }, [text, onDone])

  return (
    <span>
      {displayed}
      {displayed.length < text.length && (
        <span className="inline-block w-[2px] h-[14px] bg-[#7C8FFF] ml-0.5 align-middle animate-pulse" />
      )}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Helper: generate response from slash command
// ---------------------------------------------------------------------------

function generateResponse(
  input: string,
  nodes: GraphNode[],
  vcs: VCFirm[],
  companies: Company[],
  investments: Investment[],
): { text: string; nodeResults?: GraphNode[] } {
  const lower = input.toLowerCase().trim()

  // /search <query>
  if (lower.startsWith('/search')) {
    const q = input.slice(7).trim().toLowerCase()
    if (!q) return { text: 'What would you like to search for? Try: /search Perplexity' }
    const matches = nodes.filter(n => n.name.toLowerCase().includes(q)).slice(0, 6)
    if (matches.length === 0) return { text: `No results found for "${q}". Try a different term.` }
    const list = matches.map(n => `• ${n.name} (${n.type === 'vc' ? 'VC' : 'Company'})`).join('\n')
    return { text: `Found ${matches.length} result${matches.length > 1 ? 's' : ''}:\n${list}`, nodeResults: matches }
  }

  // /vc <name>
  if (lower.startsWith('/vc')) {
    const q = input.slice(3).trim().toLowerCase()
    if (!q) return { text: 'Which VC would you like to look up? Try: /vc Khosla' }
    const vc = vcs.find(v => v.name.toLowerCase().includes(q))
    if (!vc) return { text: `No VC found matching "${q}".` }
    const invCount = investments.filter(i => i.vc_id === vc.id).length
    const aum = vc.aum_usd ? `$${(vc.aum_usd / 1e9).toFixed(1)}B AUM` : 'AUM undisclosed'
    const stages = vc.fund_stage.join(', ')
    const sectors = vc.focus_sectors.slice(0, 4).join(', ')
    const node = nodes.find(n => n.id === vc.id)
    return {
      text: `${vc.name} — ${vc.hq_city ?? 'Unknown'}\n${vc.description ?? ''}\n\n${aum} · Founded ${vc.founded_year ?? '?'}\nStages: ${stages}\nSectors: ${sectors}\nPortfolio: ${invCount} companies tracked`,
      nodeResults: node ? [node] : undefined,
    }
  }

  // /company <name>
  if (lower.startsWith('/company')) {
    const q = input.slice(8).trim().toLowerCase()
    if (!q) return { text: 'Which company? Try: /company ElevenLabs' }
    const co = companies.find(c => c.name.toLowerCase().includes(q))
    if (!co) return { text: `No company found matching "${q}".` }
    const raised = co.total_raised_usd ? `$${(co.total_raised_usd / 1e6).toFixed(0)}M raised` : 'Funding undisclosed'
    const investors = investments.filter(i => i.company_id === co.id)
    const vcNames = investors.map(i => vcs.find(v => v.id === i.vc_id)?.name).filter(Boolean)
    const node = nodes.find(n => n.id === co.id)
    return {
      text: `${co.name} — ${co.sector ?? 'Unknown sector'}\n${co.city ?? ''}, ${co.country ?? ''} · Founded ${co.founded_year ?? '?'}\nStage: ${co.stage ?? '?'} · Status: ${co.status}\n${raised}\n${vcNames.length > 0 ? `Investors: ${vcNames.join(', ')}` : 'No tracked investors'}`,
      nodeResults: node ? [node] : undefined,
    }
  }

  // /weekly
  if (lower.startsWith('/weekly')) {
    const recentInv = [...investments]
      .sort((a, b) => (b.announced_date ?? '').localeCompare(a.announced_date ?? ''))
      .slice(0, 5)
    const lines = recentInv.map(inv => {
      const vc = vcs.find(v => v.id === inv.vc_id)
      const co = companies.find(c => c.id === inv.company_id)
      return `• ${vc?.name ?? '?'} → ${co?.name ?? '?'} (${inv.stage ?? '?'})`
    })
    return { text: `Recent activity:\n${lines.join('\n')}\n\nStay tuned — live feed coming soon.` }
  }

  // /latest
  if (lower.startsWith('/latest')) {
    const sorted = [...investments]
      .sort((a, b) => (b.announced_date ?? '').localeCompare(a.announced_date ?? ''))
      .slice(0, 6)
    const lines = sorted.map(inv => {
      const vc = vcs.find(v => v.id === inv.vc_id)
      const co = companies.find(c => c.id === inv.company_id)
      const date = inv.announced_date ?? 'Unknown'
      return `• ${date} — ${vc?.name ?? '?'} invested in ${co?.name ?? '?'} (${inv.stage ?? '?'}${inv.lead_investor ? ', Lead' : ''})`
    })
    return { text: `Latest deals:\n${lines.join('\n')}` }
  }

  // /stats
  if (lower.startsWith('/stats')) {
    const totalRaised = companies.reduce((s, c) => s + (c.total_raised_usd ?? 0), 0)
    const sectors = new Set(companies.map(c => c.sector).filter(Boolean))
    return {
      text: `VC Radar Overview:\n• ${vcs.length} VC firms tracked\n• ${companies.length} companies\n• ${investments.length} investment links\n• ${sectors.size} sectors\n• $${(totalRaised / 1e6).toFixed(0)}M total raised (tracked)`,
    }
  }

  // /sectors
  if (lower.startsWith('/sectors')) {
    const sectorMap: Record<string, number> = {}
    for (const co of companies) {
      const s = co.sector ?? 'Unknown'
      sectorMap[s] = (sectorMap[s] ?? 0) + 1
    }
    const sorted = Object.entries(sectorMap).sort((a, b) => b[1] - a[1])
    const lines = sorted.map(([s, c]) => `• ${s}: ${c} companies`)
    return { text: `Sector breakdown:\n${lines.join('\n')}` }
  }

  // /hot
  if (lower.startsWith('/hot')) {
    const vcActivity: Record<string, number> = {}
    for (const inv of investments) {
      vcActivity[inv.vc_id] = (vcActivity[inv.vc_id] ?? 0) + 1
    }
    const topVcs = Object.entries(vcActivity)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([id, count]) => {
        const vc = vcs.find(v => v.id === id)
        return `• ${vc?.name ?? '?'} — ${count} deals`
      })
    return { text: `Most active VCs:\n${topVcs.join('\n')}` }
  }

  // Free-form question — simple keyword match
  const q = lower
  if (q.includes('how many') && q.includes('vc')) {
    return { text: `There are ${vcs.length} VC firms currently tracked in VC Radar.` }
  }
  if (q.includes('how many') && q.includes('compan')) {
    return { text: `There are ${companies.length} companies currently tracked.` }
  }

  // Fallback: try searching
  const matches = nodes.filter(n => n.name.toLowerCase().includes(q)).slice(0, 4)
  if (matches.length > 0) {
    const list = matches.map(n => `• ${n.name} (${n.type === 'vc' ? 'VC' : 'Company'})`).join('\n')
    return { text: `I found these matches:\n${list}\n\nTip: use /vc or /company for detailed lookups.`, nodeResults: matches }
  }

  return {
    text: `I can help you explore the VC ecosystem. Try one of these:\n• /search <name> — Find VCs or companies\n• /vc <name> — Deep dive on a VC\n• /company <name> — Company details\n• /latest — Recent deals\n• /weekly — This week's activity\n• /stats — Overview numbers\n• /sectors — Sector breakdown\n• /hot — Most active VCs`,
  }
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function ChatPanel({
  nodes, filters, onFiltersChange, onNavigateToNode,
  vcCount, companyCount, vcs, companies, investments,
}: ChatPanelProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const [slashFilter, setSlashFilter] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isTyping])

  // Slash menu filtering
  const filteredActions = useMemo(() => {
    if (!slashFilter) return SLASH_ACTIONS
    return SLASH_ACTIONS.filter(a =>
      a.command.includes(slashFilter.toLowerCase()) ||
      a.label.toLowerCase().includes(slashFilter.toLowerCase())
    )
  }, [slashFilter])

  const handleInputChange = useCallback((val: string) => {
    setInputValue(val)
    if (val.startsWith('/')) {
      setShowSlashMenu(true)
      setSlashFilter(val)
    } else {
      setShowSlashMenu(false)
      setSlashFilter('')
    }
  }, [])

  const handleSelectAction = useCallback((action: SlashAction) => {
    setInputValue(action.command + ' ')
    setShowSlashMenu(false)
    inputRef.current?.focus()
  }, [])

  const handleSubmit = useCallback(() => {
    const text = inputValue.trim()
    if (!text || isTyping) return

    // Create user message
    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMsg])
    setInputValue('')
    setShowSlashMenu(false)
    setIsTyping(true)

    // Also update graph filter if it's a search
    if (text.startsWith('/search ')) {
      const q = text.slice(8).trim()
      onFiltersChange({ ...filters, searchQuery: q })
    }

    // Generate response (simulated delay for realism)
    setTimeout(() => {
      const { text: responseText, nodeResults } = generateResponse(
        text, nodes, vcs, companies, investments,
      )

      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: responseText,
        timestamp: Date.now(),
        nodeResults,
      }

      setMessages(prev => [...prev, assistantMsg])
      setIsTyping(false)
    }, 300 + Math.random() * 400)
  }, [inputValue, isTyping, nodes, vcs, companies, investments, filters, onFiltersChange])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
    if (e.key === 'Escape') {
      setShowSlashMenu(false)
    }
  }, [handleSubmit])

  // ---- Collapsed state ----
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
          onClick={() => { setCollapsed(false); inputRef.current?.focus() }}
          className="p-2 rounded-lg text-[#64748B] hover:text-[#E2E8F0] transition-colors"
        >
          <Sparkles className="w-4 h-4" />
        </button>
      </div>
    )
  }

  // ---- Expanded state ----
  return (
    <motion.div
      initial={{ x: -380, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ type: 'spring', damping: 30, stiffness: 400 }}
      className="fixed left-4 top-20 z-40 glass-panel flex flex-col overflow-hidden"
      style={{ width: '360px', height: 'calc(100vh - 96px)' }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(124, 143, 255, 0.12)' }}
          >
            <Sparkles className="w-3.5 h-3.5 text-[#7C8FFF]" />
          </div>
          <div>
            <p className="text-sm font-medium text-[#E2E8F0]">VC Radar</p>
            <p className="text-[10px] text-[#475569]">{vcCount} VCs · {companyCount} companies</p>
          </div>
        </div>
        <button
          onClick={() => setCollapsed(true)}
          className="p-1.5 rounded-lg text-[#475569] hover:text-[#94A3B8] transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(148,163,184,0.08), transparent)' }} />

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 ? (
          /* Empty state — show quick actions */
          <div className="space-y-4 pt-2">
            <p className="text-xs text-[#475569] text-center">
              Ask anything or use a slash command
            </p>

            {/* Quick action chips */}
            <div className="flex flex-wrap gap-1.5">
              {SLASH_ACTIONS.map(action => (
                <button
                  key={action.command}
                  onClick={() => handleSelectAction(action)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-[#94A3B8] hover:text-[#E2E8F0] transition-all"
                  style={{
                    background: 'rgba(15, 23, 42, 0.5)',
                    border: '1px solid rgba(148, 163, 184, 0.06)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'rgba(124, 143, 255, 0.15)'
                    e.currentTarget.style.background = 'rgba(124, 143, 255, 0.06)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'rgba(148, 163, 184, 0.06)'
                    e.currentTarget.style.background = 'rgba(15, 23, 42, 0.5)'
                  }}
                >
                  <span className="text-[#7C8FFF]">{action.icon}</span>
                  <span>{action.label}</span>
                </button>
              ))}
            </div>

            {/* Divider */}
            <div className="h-px" style={{ background: 'linear-gradient(to right, transparent, rgba(148,163,184,0.06), transparent)' }} />

            {/* Filters (compact) */}
            <div>
              <p className="text-[10px] font-semibold text-[#475569] uppercase tracking-wider mb-2">Filters</p>
              <div className="flex gap-2">
                <button
                  onClick={() => onFiltersChange({ ...filters, showVCs: !filters.showVCs })}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition-colors"
                  style={{
                    background: filters.showVCs ? 'rgba(124, 143, 255, 0.10)' : 'rgba(15, 23, 42, 0.4)',
                    border: `1px solid ${filters.showVCs ? 'rgba(124, 143, 255, 0.20)' : 'rgba(148, 163, 184, 0.06)'}`,
                    color: filters.showVCs ? '#A5B4FC' : '#475569',
                  }}
                >
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: filters.showVCs ? '#7C8FFF' : '#334155' }} />
                  VCs ({vcCount})
                </button>
                <button
                  onClick={() => onFiltersChange({ ...filters, showCompanies: !filters.showCompanies })}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] transition-colors"
                  style={{
                    background: filters.showCompanies ? 'rgba(56, 189, 248, 0.10)' : 'rgba(15, 23, 42, 0.4)',
                    border: `1px solid ${filters.showCompanies ? 'rgba(56, 189, 248, 0.20)' : 'rgba(148, 163, 184, 0.06)'}`,
                    color: filters.showCompanies ? '#67E8F9' : '#475569',
                  }}
                >
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: filters.showCompanies ? '#38BDF8' : '#334155' }} />
                  Companies ({companyCount})
                </button>
              </div>
            </div>

            {/* Hint */}
            <p className="text-[10px] text-[#1E293B] text-center pt-4">
              Type <span className="text-[#475569]">/</span> to see all commands
            </p>
          </div>
        ) : (
          /* Message bubbles */
          <>
            {messages.map((msg, i) => (
              <div key={msg.id}>
                {msg.role === 'user' ? (
                  <div className="flex justify-end">
                    <div
                      className="max-w-[85%] px-3 py-2 rounded-2xl rounded-tr-md text-sm text-[#E2E8F0]"
                      style={{ background: 'rgba(124, 143, 255, 0.15)', border: '1px solid rgba(124, 143, 255, 0.10)' }}
                    >
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="max-w-[90%]">
                      <div
                        className="px-3 py-2 rounded-2xl rounded-tl-md text-sm text-[#C8D1E0] whitespace-pre-line"
                        style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(148, 163, 184, 0.06)' }}
                      >
                        {i === messages.length - 1 && msg.role === 'assistant' ? (
                          <TypewriterText text={msg.content} />
                        ) : (
                          msg.content
                        )}
                      </div>
                      {/* Clickable node results */}
                      {msg.nodeResults && msg.nodeResults.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {msg.nodeResults.map(node => (
                            <button
                              key={node.id}
                              onClick={() => onNavigateToNode(node.id)}
                              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] hover:brightness-125 transition-all"
                              style={{
                                background: node.type === 'vc' ? 'rgba(124, 143, 255, 0.10)' : 'rgba(56, 189, 248, 0.10)',
                                border: `1px solid ${node.type === 'vc' ? 'rgba(124, 143, 255, 0.15)' : 'rgba(56, 189, 248, 0.15)'}`,
                                color: node.type === 'vc' ? '#A5B4FC' : '#67E8F9',
                              }}
                            >
                              <span
                                className="w-1.5 h-1.5 rounded-full"
                                style={{ backgroundColor: node.type === 'vc' ? '#7C8FFF' : '#38BDF8' }}
                              />
                              {node.name}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="flex justify-start">
                <div
                  className="px-3 py-2.5 rounded-2xl rounded-tl-md"
                  style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(148, 163, 184, 0.06)' }}
                >
                  <div className="flex gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#7C8FFF] animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#7C8FFF] animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#7C8FFF] animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Slash command menu */}
      <AnimatePresence>
        {showSlashMenu && filteredActions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.15 }}
            className="mx-4 mb-2 rounded-xl overflow-hidden"
            style={{
              background: 'rgba(15, 23, 42, 0.92)',
              border: '1px solid rgba(148, 163, 184, 0.08)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
            }}
          >
            <div className="p-1.5 max-h-[200px] overflow-y-auto">
              {filteredActions.map(action => (
                <button
                  key={action.command}
                  onClick={() => handleSelectAction(action)}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white/[0.04] transition-colors text-left"
                >
                  <span className="text-[#7C8FFF]">{action.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[#E2E8F0]">{action.command}</span>
                      <span className="text-[10px] text-[#475569]">{action.description}</span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input bar */}
      <div className="px-3 pb-3 pt-1">
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-xl transition-all"
          style={{
            background: 'rgba(15, 23, 42, 0.5)',
            border: '1px solid rgba(148, 163, 184, 0.06)',
          }}
        >
          <input
            ref={inputRef}
            type="text"
            placeholder="Ask anything or type / ..."
            value={inputValue}
            onChange={e => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={e => {
              const parent = e.target.parentElement!
              parent.style.boxShadow = '0 0 0 3px rgba(124, 143, 255, 0.12), 0 0 16px rgba(124, 143, 255, 0.08)'
              parent.style.borderColor = 'rgba(124, 143, 255, 0.2)'
            }}
            onBlur={e => {
              const parent = e.target.parentElement!
              parent.style.boxShadow = 'none'
              parent.style.borderColor = 'rgba(148, 163, 184, 0.06)'
            }}
            className="flex-1 bg-transparent text-sm text-[#E2E8F0] placeholder:text-[#334155] focus:outline-none"
          />
          <button
            onClick={handleSubmit}
            disabled={!inputValue.trim() || isTyping}
            className="p-1.5 rounded-lg transition-all disabled:opacity-20"
            style={{
              background: inputValue.trim() ? 'rgba(124, 143, 255, 0.15)' : 'transparent',
            }}
          >
            <Send className="w-3.5 h-3.5 text-[#7C8FFF]" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}
