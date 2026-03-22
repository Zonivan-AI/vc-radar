'use client'

import { useState, useRef, useCallback, useMemo, useEffect } from 'react'
import { Radio } from 'lucide-react'
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
      {/* Background gradient overlay */}
      <div
        className="absolute inset-0 pointer-events-none z-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, #0F1629 0%, #060A14 70%)',
        }}
      />

      {/* Loading overlay */}
      {isLoading && (
        <div
          className="absolute inset-0 z-50 flex flex-col items-center justify-center transition-opacity duration-500"
          style={{ background: 'radial-gradient(ellipse at 50% 50%, #0F1629 0%, #060A14 70%)' }}
        >
          <div className="glass-panel p-8 flex flex-col items-center">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: 'rgba(124, 143, 255, 0.12)' }}>
              <Radio className="w-5 h-5 text-[#7C8FFF]" />
            </div>
            <p className="text-sm font-medium text-[#E2E8F0] mb-4">VC Radar</p>
            <div className="flex gap-2">
              <span className="w-1.5 h-1.5 rounded-full animate-breathe" style={{ backgroundColor: '#7C8FFF', animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-breathe" style={{ backgroundColor: '#7C8FFF', animationDelay: '300ms' }} />
              <span className="w-1.5 h-1.5 rounded-full animate-breathe" style={{ backgroundColor: '#7C8FFF', animationDelay: '600ms' }} />
            </div>
          </div>
        </div>
      )}

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
