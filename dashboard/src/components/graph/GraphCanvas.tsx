'use client'

import { useRef, useCallback, useEffect, useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import type { GraphNode, GraphLink, GraphData, GraphFilters } from '@/lib/graph-types'
import { FORCE_CONFIG } from '@/lib/graph-forces'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

// New 2-tone palette
const COLORS = {
  vc: '#7C8FFF',
  vcHover: '#A5B4FC',
  company: '#38BDF8',
  companyHover: '#67E8F9',
  linkInvestment: '#7C8FFF',
  linkCoInvestor: '#64748B',
  linkHighlight: '#7C8FFFCC',
  linkDimmed: '#FFFFFF08',
  background: '#060A14',
}

interface GraphCanvasProps {
  graphData: GraphData
  filters: GraphFilters
  hoveredNode: GraphNode | null
  selectedNode: GraphNode | null
  onNodeHover: (node: GraphNode | null, event: MouseEvent | null) => void
  onNodeClick: (node: GraphNode) => void
  onEngineStop: () => void
  graphRef: React.MutableRefObject<any>
}

export function GraphCanvas({
  graphData,
  filters,
  hoveredNode,
  selectedNode,
  onNodeHover,
  onNodeClick,
  onEngineStop,
  graphRef,
}: GraphCanvasProps) {
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const update = () => {
      setDimensions({ width: window.innerWidth, height: window.innerHeight - 64 })
    }
    update()
    window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])

  // Filter graph data based on filters
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes
    let links = graphData.links

    if (!filters.showVCs) {
      const vcIds = new Set(nodes.filter(n => n.type === 'vc').map(n => n.id))
      nodes = nodes.filter(n => n.type !== 'vc')
      links = links.filter(l => {
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        return !vcIds.has(sourceId) && !vcIds.has(targetId)
      })
    }

    if (!filters.showCompanies) {
      const companyIds = new Set(nodes.filter(n => n.type === 'company').map(n => n.id))
      nodes = nodes.filter(n => n.type !== 'company')
      links = links.filter(l => {
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        return !companyIds.has(sourceId) && !companyIds.has(targetId)
      })
    }

    if (filters.sectors.length > 0) {
      const sectorFilter = new Set(filters.sectors)
      nodes = nodes.filter(n => {
        if (n.type === 'vc') return true
        const company = n.data as any
        return company.sector && sectorFilter.has(company.sector)
      })
      const nodeIds = new Set(nodes.map(n => n.id))
      links = links.filter(l => {
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
    }

    return { nodes, links }
  }, [graphData, filters])

  // Compute highlight sets for hover
  const highlightNodes = useMemo(() => {
    if (!hoveredNode) return new Set<string>()
    const set = new Set<string>([hoveredNode.id])
    for (const link of graphData.links) {
      const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target
      if (sourceId === hoveredNode.id) set.add(targetId)
      if (targetId === hoveredNode.id) set.add(sourceId)
    }
    return set
  }, [hoveredNode, graphData.links])

  const highlightLinks = useMemo(() => {
    if (!hoveredNode) return new Set<string>()
    const set = new Set<string>()
    for (const link of graphData.links) {
      const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target
      if (sourceId === hoveredNode.id || targetId === hoveredNode.id) {
        set.add(`${sourceId}-${targetId}`)
      }
    }
    return set
  }, [hoveredNode, graphData.links])

  // Configure forces after mount
  useEffect(() => {
    if (!graphRef.current) return
    const fg = graphRef.current

    fg.d3Force('charge')?.strength((node: GraphNode) => FORCE_CONFIG.charge.strength(node))
    fg.d3Force('charge')?.distanceMax(FORCE_CONFIG.charge.distanceMax)
    fg.d3Force('link')?.distance((link: GraphLink) => FORCE_CONFIG.link.distance(link))
    fg.d3Force('link')?.strength((link: GraphLink) => FORCE_CONFIG.link.strength(link))
    fg.d3Force('center')?.strength(FORCE_CONFIG.center.strength)
  }, [graphRef, filteredData])

  const handleNodeHover = useCallback((node: any, prevNode: any) => {
    onNodeHover(node as GraphNode | null, null)
  }, [onNodeHover])

  const handleNodeClick = useCallback((node: any) => {
    onNodeClick(node as GraphNode)
    // Camera fly-to
    if (graphRef.current && node) {
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
    }
  }, [onNodeClick, graphRef])

  if (dimensions.width === 0) return null

  return (
    <ForceGraph3D
      ref={graphRef}
      width={dimensions.width}
      height={dimensions.height}
      graphData={filteredData}
      backgroundColor={COLORS.background}
      nodeId="id"
      nodeLabel=""
      nodeVal={(node: any) => (node as GraphNode).size}
      nodeColor={(node: any) => {
        const n = node as GraphNode
        if (hoveredNode) {
          if (n.id === hoveredNode.id) {
            return n.type === 'vc' ? COLORS.vcHover : COLORS.companyHover
          }
          if (highlightNodes.has(n.id)) {
            return n.type === 'vc' ? COLORS.vc : COLORS.company
          }
          // Dimmed — 12% opacity
          return n.type === 'vc' ? '#7C8FFF1F' : '#38BDF81F'
        }
        if (selectedNode && n.id === selectedNode.id) {
          return n.type === 'vc' ? COLORS.vcHover : COLORS.companyHover
        }
        return n.type === 'vc' ? COLORS.vc : COLORS.company
      }}
      nodeOpacity={1}
      nodeResolution={20}
      linkColor={(link: any) => {
        const l = link as GraphLink
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        const linkKey = `${sourceId}-${targetId}`

        if (hoveredNode) {
          if (highlightLinks.has(linkKey)) return COLORS.linkHighlight
          return COLORS.linkDimmed
        }
        if (l.type === 'co-investor') return '#64748B40'
        return l.strength > 0.8 ? '#7C8FFF73' : '#7C8FFF40'
      }}
      linkWidth={(link: any) => {
        const l = link as GraphLink
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        const linkKey = `${sourceId}-${targetId}`

        if (hoveredNode && highlightLinks.has(linkKey)) return 2.5
        if (l.type === 'co-investor') return 0.5
        return l.strength > 0.8 ? 2 : 1
      }}
      linkDirectionalParticles={(link: any) => {
        const l = link as GraphLink
        if (l.type !== 'investment') return 0
        return l.strength > 0.8 ? 2 : 1
      }}
      linkDirectionalParticleWidth={1.5}
      linkDirectionalParticleSpeed={0.004}
      linkDirectionalParticleColor={() => '#A5B4FC'}
      onNodeHover={handleNodeHover}
      onNodeClick={handleNodeClick}
      warmupTicks={FORCE_CONFIG.warmupTicks}
      cooldownTime={3000}
      enableNodeDrag={true}
      enableNavigationControls={true}
      showNavInfo={false}
      onEngineStop={onEngineStop}
    />
  )
}
