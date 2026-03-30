'use client'

import { useState, useRef, useCallback, useMemo, useEffect } from 'react'
import { Radio } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { RadarLogo } from '@/components/ui/radar-logo'
import type { VCFirm, Company, Investment } from '@/lib/types'
import type { GraphNode, GraphFilters } from '@/lib/graph-types'
import { buildGraphData } from '@/lib/graph-data'
import { GraphCanvas } from './GraphCanvas'
import { GraphTooltip } from './GraphTooltip'
import { NodeDetailPanel } from './NodeDetailPanel'
import { ChatPanel } from './ChatPanel'
import { GraphControls } from './GraphControls'
import { GraphLegend } from './GraphLegend'

interface GraphPageProps {
  vcs: VCFirm[]
  companies: Company[]
  investments: Investment[]
}

export function GraphPage({ vcs, companies, investments }: GraphPageProps) {
  const graphRef = useRef<any>(null)

  const graphData = useMemo(
    () => buildGraphData(vcs, companies, investments),
    [vcs, companies, investments],
  )

  const vcCount = useMemo(() => graphData.nodes.filter(n => n.type === 'vc').length, [graphData])
  const companyCount = useMemo(() => graphData.nodes.filter(n => n.type === 'company').length, [graphData])

  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [filters, setFilters] = useState<GraphFilters>({
    showVCs: true,
    showCompanies: true,
    sectors: [],
    searchQuery: '',
  })
  const [isLoading, setIsLoading] = useState(true)

  // Fallback: auto-dismiss loading after 6s even if engine hasn't stopped
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 6000)
    return () => clearTimeout(timer)
  }, [])

  // Get connected nodes for the detail panel
  const connectedNodes = useMemo(() => {
    if (!selectedNode) return []
    const connected = new Set<string>()
    for (const link of graphData.links) {
      const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target
      if (sourceId === selectedNode.id) connected.add(targetId)
      if (targetId === selectedNode.id) connected.add(sourceId)
    }
    return graphData.nodes.filter(n => connected.has(n.id))
  }, [selectedNode, graphData])

  // Track mouse position continuously for tooltip
  const mousePosRef = useRef({ x: 0, y: 0 })
  const hoveredNodeRef = useRef<GraphNode | null>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      mousePosRef.current = { x: e.clientX, y: e.clientY }
      if (hoveredNodeRef.current) {
        setTooltipPos({ x: e.clientX, y: e.clientY })
      }
    }
    window.addEventListener('mousemove', handler)
    return () => window.removeEventListener('mousemove', handler)
  }, [])

  const handleNodeHover = useCallback((node: GraphNode | null, _event: MouseEvent | null) => {
    hoveredNodeRef.current = node
    setHoveredNode(node)
    if (node) {
      setTooltipPos({ ...mousePosRef.current })
    } else {
      setTooltipPos(null)
    }
  }, [])

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(prev => (prev?.id === node.id ? null : node))
  }, [])

  const handleNavigateToNode = useCallback((nodeId: string) => {
    const node = graphData.nodes.find(n => n.id === nodeId)
    if (!node || !graphRef.current) return

    setSelectedNode(node)

    const distance = 120
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0)
    graphRef.current.cameraPosition(
      {
        x: (node.x || 0) * distRatio,
        y: (node.y || 0) * distRatio,
        z: (node.z || 0) * distRatio,
      },
      node,
      1000,
    )
  }, [graphData.nodes])

  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.cameraPosition({ x: 0, y: 0, z: 400 }, { x: 0, y: 0, z: 0 }, 1000)
    }
  }, [])

  const handleZoomIn = useCallback(() => {
    if (graphRef.current) {
      const pos = graphRef.current.cameraPosition()
      graphRef.current.cameraPosition(
        { x: pos.x * 0.7, y: pos.y * 0.7, z: pos.z * 0.7 },
        undefined,
        500,
      )
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (graphRef.current) {
      const pos = graphRef.current.cameraPosition()
      graphRef.current.cameraPosition(
        { x: pos.x * 1.4, y: pos.y * 1.4, z: pos.z * 1.4 },
        undefined,
        500,
      )
    }
  }, [])

  const handleEngineStop = useCallback(() => {
    setIsLoading(false)
  }, [])

  return (
    <div className="relative w-full h-[calc(100vh-64px)] overflow-hidden">
      {/* Background gradient overlay - warm parchment */}
      <div
        className="absolute inset-0 pointer-events-none z-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 40%, #FBF9F4 0%, #F3EDE0 60%, #EAE1D0 100%)',
        }}
      />

      {/* Subtle grid lines - cartographic feel */}
      <div
        className="absolute inset-0 pointer-events-none z-[1]"
        style={{
          backgroundImage: 'linear-gradient(rgba(180,165,140,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(180,165,140,0.06) 1px, transparent 1px)',
          backgroundSize: '60px 60px',
        }}
      />

      {/* Cinematic vignette overlay — subtle edge darkening */}
      <div
        className="absolute inset-0 pointer-events-none z-[2]"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(180,165,140,0.15) 100%)',
        }}
      />

      {/* Loading overlay */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="absolute inset-0 z-50 flex flex-col items-center justify-center"
            style={{
              background: 'radial-gradient(ellipse at 50% 40%, #FBF9F4 0%, #F3EDE0 60%, #EAE1D0 100%)',
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
              className="glass-panel p-12 flex flex-col items-center text-center"
            >
              {/* Animated radar logo with pulse rings */}
              <div className="relative mb-6">
                {/* Outer pulse ring */}
                <div
                  className="absolute -inset-4 rounded-full"
                  style={{
                    border: '1px solid rgba(180, 83, 9, 0.12)',
                    animation: 'radar-pulse 2.5s ease-out infinite',
                  }}
                />
                {/* Middle pulse ring */}
                <div
                  className="absolute -inset-2 rounded-full"
                  style={{
                    border: '1px solid rgba(180, 83, 9, 0.18)',
                    animation: 'radar-pulse 2.5s ease-out infinite 0.4s',
                  }}
                />
                <RadarLogo size="lg" animate className="rounded-2xl" />
              </div>

              <h1 className="text-xl font-bold text-[#292524] mb-1">VC Radar</h1>
              <p className="text-sm text-[#78716C] mb-6 max-w-[280px]">
                Scanning the venture capital landscape
              </p>

              {/* Stats preview */}
              <div className="flex gap-8 mb-6">
                <div className="text-center">
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="text-lg font-bold text-[#B45309]"
                  >
                    {vcCount}
                  </motion.div>
                  <div className="text-[10px] text-[#A8A29E] uppercase tracking-wider">VCs</div>
                </div>
                <div className="text-center">
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.45 }}
                    className="text-lg font-bold text-[#78716C]"
                  >
                    {companyCount.toLocaleString()}
                  </motion.div>
                  <div className="text-[10px] text-[#A8A29E] uppercase tracking-wider">Companies</div>
                </div>
                <div className="text-center">
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="text-lg font-bold text-[#57534E]"
                  >
                    {graphData.links.length.toLocaleString()}
                  </motion.div>
                  <div className="text-[10px] text-[#A8A29E] uppercase tracking-wider">Links</div>
                </div>
              </div>

              {/* Radar sweep bar */}
              <div className="w-48 h-1 bg-stone-200/60 rounded-full overflow-hidden">
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: 'linear-gradient(90deg, transparent, #B45309, transparent)' }}
                  initial={{ x: '-100%' }}
                  animate={{ x: '200%' }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3D Graph */}
      <GraphCanvas
        graphData={graphData}
        filters={filters}
        hoveredNode={hoveredNode}
        selectedNode={selectedNode}
        onNodeHover={handleNodeHover}
        onNodeClick={handleNodeClick}
        onEngineStop={handleEngineStop}
        graphRef={graphRef}
      />

      {/* Tooltip */}
      <GraphTooltip node={hoveredNode} position={tooltipPos} />

      {/* Chat/Search Panel */}
      <ChatPanel
        nodes={graphData.nodes}
        filters={filters}
        onFiltersChange={setFilters}
        onNavigateToNode={handleNavigateToNode}
        vcCount={vcCount}
        companyCount={companyCount}
        vcs={vcs}
        companies={companies}
        investments={investments}
      />

      {/* Detail Panel */}
      <NodeDetailPanel
        node={selectedNode}
        onClose={() => setSelectedNode(null)}
        onNavigateToNode={handleNavigateToNode}
        connectedNodes={connectedNodes}
      />

      {/* Controls & Legend */}
      <GraphControls
        onResetView={handleResetView}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
      />
      <GraphLegend />
    </div>
  )
}
