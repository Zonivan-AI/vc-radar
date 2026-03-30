'use client'

import { useRef, useCallback, useEffect, useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import * as THREE from 'three'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import type { GraphNode, GraphLink, GraphData, GraphFilters } from '@/lib/graph-types'
import { FORCE_CONFIG } from '@/lib/graph-forces'
import { VC_GRADIENT } from '@/lib/graph-colors'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

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

// ─── Sprite helpers ──────────────────────────────────────────────────────────

function makeGlowTexture(color: string): THREE.CanvasTexture {
  const sz = 128
  const canvas = document.createElement('canvas')
  canvas.width = sz
  canvas.height = sz
  const ctx = canvas.getContext('2d')!
  const c = sz / 2

  const gradient = ctx.createRadialGradient(c, c, 0, c, c, c)
  gradient.addColorStop(0, color + 'FF')
  gradient.addColorStop(0.12, color + 'CC')
  gradient.addColorStop(0.3, color + '55')
  gradient.addColorStop(0.6, color + '18')
  gradient.addColorStop(1, color + '00')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, sz, sz)

  // Bright core
  const coreGrad = ctx.createRadialGradient(c, c, 0, c, c, c * 0.35)
  coreGrad.addColorStop(0, '#FFFFFFDD')
  coreGrad.addColorStop(0.4, color + 'AA')
  coreGrad.addColorStop(1, color + '00')
  ctx.fillStyle = coreGrad
  ctx.beginPath()
  ctx.arc(c, c, c * 0.4, 0, Math.PI * 2)
  ctx.fill()

  const tex = new THREE.CanvasTexture(canvas)
  return tex
}

function makeLabelTexture(text: string, color: string = '#292524'): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  const fontSize = 52
  ctx.font = `600 ${fontSize}px "DM Sans", Inter, system-ui, sans-serif`
  const metrics = ctx.measureText(text)
  const pad = 20
  const w = metrics.width + pad * 2
  const h = fontSize * 1.8

  canvas.width = w
  canvas.height = h
  ctx.font = `600 ${fontSize}px "DM Sans", Inter, system-ui, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  // Shadow for readability on warm parchment background
  ctx.shadowColor = '#FFFFFF99'
  ctx.shadowBlur = 12
  ctx.shadowOffsetY = 1
  ctx.fillStyle = color
  ctx.fillText(text, w / 2, h / 2)

  const tex = new THREE.CanvasTexture(canvas)
  tex.minFilter = THREE.LinearFilter
  return tex
}

// Ring texture for pulse effect on VC nodes
function makeRingTexture(color: string): THREE.CanvasTexture {
  const sz = 128
  const canvas = document.createElement('canvas')
  canvas.width = sz
  canvas.height = sz
  const ctx = canvas.getContext('2d')!
  const c = sz / 2

  ctx.beginPath()
  ctx.arc(c, c, c * 0.75, 0, Math.PI * 2)
  ctx.lineWidth = 2
  ctx.strokeStyle = color + '60'
  ctx.stroke()

  ctx.beginPath()
  ctx.arc(c, c, c * 0.55, 0, Math.PI * 2)
  ctx.lineWidth = 1.5
  ctx.strokeStyle = color + '30'
  ctx.stroke()

  const tex = new THREE.CanvasTexture(canvas)
  return tex
}

// Texture caches
const glowTextureCache = new Map<string, THREE.CanvasTexture>()
function getCachedGlowTexture(color: string) {
  if (!glowTextureCache.has(color)) {
    glowTextureCache.set(color, makeGlowTexture(color))
  }
  return glowTextureCache.get(color)!
}

const labelTextureCache = new Map<string, THREE.CanvasTexture>()
function getCachedLabelTexture(text: string, color: string) {
  const key = `${text}|${color}`
  if (!labelTextureCache.has(key)) {
    labelTextureCache.set(key, makeLabelTexture(text, color))
  }
  return labelTextureCache.get(key)!
}

const ringTextureCache = new Map<string, THREE.CanvasTexture>()
function getCachedRingTexture(color: string) {
  if (!ringTextureCache.has(color)) {
    ringTextureCache.set(color, makeRingTexture(color))
  }
  return ringTextureCache.get(color)!
}

// ─── Component ───────────────────────────────────────────────────────────────

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
  const nodeObjectsRef = useRef(new Map<string, THREE.Group>())
  const bloomPassRef = useRef<UnrealBloomPass | null>(null)
  const animationFrameRef = useRef<number>(0)
  const startTimeRef = useRef(performance.now())
  const autoOrbitRef = useRef({ enabled: true, angle: 0, speed: 0.03 })
  const initialRevealDoneRef = useRef(false)

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

  // Top VCs by connection count — always show labels
  const topVCIds = useMemo(() => {
    const connectionCount = new Map<string, number>()
    for (const link of graphData.links) {
      const sourceId = typeof link.source === 'object' ? (link.source as any).id : link.source
      const targetId = typeof link.target === 'object' ? (link.target as any).id : link.target
      connectionCount.set(sourceId, (connectionCount.get(sourceId) || 0) + 1)
      connectionCount.set(targetId, (connectionCount.get(targetId) || 0) + 1)
    }
    return new Set(
      graphData.nodes
        .filter(n => n.type === 'vc')
        .sort((a, b) => (connectionCount.get(b.id) || 0) - (connectionCount.get(a.id) || 0))
        .slice(0, 50) // Show more labels (was 40)
        .map(n => n.id),
    )
  }, [graphData])

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

  // ─── Scene setup: fog, bloom, tone mapping, lights ──────────────────────────
  useEffect(() => {
    if (!graphRef.current) return
    const renderer = graphRef.current.renderer()
    const scene = graphRef.current.scene()

    if (renderer) {
      renderer.toneMapping = THREE.ACESFilmicToneMapping
      renderer.toneMappingExposure = 1.1
    }

    if (scene) {
      // Enhanced atmospheric fog — stronger density for depth
      scene.fog = new THREE.FogExp2(0xF3EDE0, 0.0012)

      // Add warm ambient light
      const existingAmbient = scene.getObjectByName('warmAmbient')
      if (!existingAmbient) {
        const ambient = new THREE.AmbientLight(0xFFF8F0, 0.6)
        ambient.name = 'warmAmbient'
        scene.add(ambient)

        // Warm directional light from above-left
        const dirLight = new THREE.DirectionalLight(0xFFF0E0, 0.4)
        dirLight.position.set(-200, 300, 200)
        dirLight.name = 'warmDir'
        scene.add(dirLight)

        // Subtle point light for center glow
        const pointLight = new THREE.PointLight(0xD97706, 0.3, 800)
        pointLight.position.set(0, 0, 0)
        pointLight.name = 'centerGlow'
        scene.add(pointLight)
      }
    }

    // ─── UnrealBloomPass (warm bloom) ─────────────────────────────────
    try {
      const composer = graphRef.current.postProcessingComposer()
      if (composer && !bloomPassRef.current) {
        const bloomPass = new UnrealBloomPass(
          new THREE.Vector2(dimensions.width, dimensions.height),
          0.6,   // strength — subtle warm glow, not overblown
          0.8,   // radius — wide soft spread
          0.7,   // threshold — only bright nodes bloom
        )
        composer.addPass(bloomPass)
        bloomPassRef.current = bloomPass
      }
    } catch (e) {
      // postProcessingComposer may not be available immediately
      console.warn('Bloom setup deferred:', e)
    }
  }, [graphRef, dimensions])

  // ─── Cinematic idle auto-orbit ──────────────────────────────────────────────
  useEffect(() => {
    const orbit = autoOrbitRef.current

    const animate = () => {
      if (!graphRef.current || !orbit.enabled) {
        animationFrameRef.current = requestAnimationFrame(animate)
        return
      }

      const elapsed = (performance.now() - startTimeRef.current) / 1000

      // Gentle pulse on ring sprites
      nodeObjectsRef.current.forEach((group) => {
        const ring = group.getObjectByName('ring') as THREE.Sprite | undefined
        if (ring) {
          const pulse = 1 + Math.sin(elapsed * 1.5 + (group as any).__phaseOffset) * 0.15
          const baseScale = (ring as any).__baseScale || 1
          ring.scale.setScalar(baseScale * pulse)
          const ringMat = ring.material as THREE.SpriteMaterial
          ringMat.opacity = 0.15 + Math.sin(elapsed * 1.5 + (group as any).__phaseOffset) * 0.1
        }
      })

      animationFrameRef.current = requestAnimationFrame(animate)
    }

    startTimeRef.current = performance.now()
    animationFrameRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animationFrameRef.current)
    }
  }, [graphRef])

  // Disable auto-orbit when user interacts
  useEffect(() => {
    if (hoveredNode || selectedNode) {
      autoOrbitRef.current.enabled = false
    }
  }, [hoveredNode, selectedNode])

  // ─── Initial cinematic reveal — zoom in from far away ────────────────────
  const handleEngineStop = useCallback(() => {
    onEngineStop()

    if (!initialRevealDoneRef.current && graphRef.current) {
      initialRevealDoneRef.current = true
      // Start far away, zoom in smoothly
      graphRef.current.cameraPosition(
        { x: 0, y: 80, z: 500 }, // Start position (already set by default)
        { x: 0, y: 0, z: 0 },
        0, // instant
      )
      // Then animate to final position
      setTimeout(() => {
        graphRef.current?.cameraPosition(
          { x: 0, y: 50, z: 350 },
          { x: 0, y: 0, z: 0 },
          2500,
        )
      }, 100)
    }
  }, [onEngineStop, graphRef])

  // ─── Node creation (called once per node) ───────────────────────────────
  const nodeThreeObject = useCallback((node: any) => {
    const n = node as GraphNode
    const group = new THREE.Group()
    ;(group as any).__nodeId = n.id
    ;(group as any).__nodeType = n.type
    ;(group as any).__phaseOffset = Math.random() * Math.PI * 2

    const radius = n.type === 'vc' ? n.size * 0.55 : n.size * 0.4

    // Core sphere — upgraded to MeshStandardMaterial for metallic sheen
    const geometry = new THREE.SphereGeometry(radius, 32, 32) // Higher poly count (was 24)
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(n.color),
      emissive: new THREE.Color(n.color),
      emissiveIntensity: n.type === 'vc' ? 0.6 : 0.4,
      metalness: n.type === 'vc' ? 0.3 : 0.1,
      roughness: n.type === 'vc' ? 0.4 : 0.7,
      transparent: true,
      opacity: 1,
    })
    const sphere = new THREE.Mesh(geometry, material)
    sphere.name = 'core'
    group.add(sphere)

    // Glow sprite — warmer, softer
    const glowTex = getCachedGlowTexture(n.glowColor || n.color)
    const glowMat = new THREE.SpriteMaterial({
      map: glowTex,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: n.type === 'vc' ? 0.7 : 0.5,
    })
    const glow = new THREE.Sprite(glowMat.clone())
    glow.name = 'glow'
    const glowScale = n.type === 'vc' ? radius * 6 : radius * 4.5
    glow.scale.set(glowScale, glowScale, 1)
    group.add(glow)

    // Pulse ring for VC nodes — subtle animated ring
    if (n.type === 'vc') {
      const ringTex = getCachedRingTexture(n.glowColor || n.color)
      const ringMat = new THREE.SpriteMaterial({
        map: ringTex,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        opacity: 0.2,
      })
      const ring = new THREE.Sprite(ringMat)
      ring.name = 'ring'
      const ringScale = radius * 4
      ring.scale.set(ringScale, ringScale, 1)
      ;(ring as any).__baseScale = ringScale
      group.add(ring)
    }

    // Label for top VCs
    if (n.type === 'vc' && topVCIds.has(n.id)) {
      const labelColor = '#292524'
      const labelTex = getCachedLabelTexture(n.name, labelColor)
      const labelMat = new THREE.SpriteMaterial({
        map: labelTex,
        transparent: true,
        depthWrite: false,
        opacity: 0.9,
      })
      const label = new THREE.Sprite(labelMat)
      label.name = 'label'
      const aspect = labelTex.image.width / labelTex.image.height
      const labelHeight = 5
      label.scale.set(labelHeight * aspect, labelHeight, 1)
      label.position.set(0, radius + 6, 0)
      group.add(label)
    }

    // Store reference for dynamic updates
    nodeObjectsRef.current.set(n.id, group)

    return group
  }, [topVCIds])

  // ─── Dynamic hover/select effects via material updates ─────────────────────
  useEffect(() => {
    const objects = nodeObjectsRef.current
    if (objects.size === 0) return

    objects.forEach((group, nodeId) => {
      const nodeType = (group as any).__nodeType as string
      const core = group.getObjectByName('core') as THREE.Mesh | undefined
      const glow = group.getObjectByName('glow') as THREE.Sprite | undefined
      const label = group.getObjectByName('label') as THREE.Sprite | undefined
      const ring = group.getObjectByName('ring') as THREE.Sprite | undefined

      if (!core) return
      const mat = core.material as THREE.MeshStandardMaterial

      if (hoveredNode) {
        if (nodeId === hoveredNode.id) {
          // Hovered node — bright and prominent
          mat.opacity = 1
          mat.emissiveIntensity = 1.0
          group.scale.setScalar(1.3) // Scale up on hover
          if (glow) (glow.material as THREE.SpriteMaterial).opacity = 1.0
          if (label) (label.material as THREE.SpriteMaterial).opacity = 1
          if (ring) (ring.material as THREE.SpriteMaterial).opacity = 0.5
        } else if (highlightNodes.has(nodeId)) {
          // Connected to hovered — visible
          mat.opacity = 1
          mat.emissiveIntensity = 0.6
          group.scale.setScalar(1.1) // Slight bump
          if (glow) (glow.material as THREE.SpriteMaterial).opacity = 0.6
          if (label) (label.material as THREE.SpriteMaterial).opacity = 0.8
          if (ring) (ring.material as THREE.SpriteMaterial).opacity = 0.3
        } else {
          // Dimmed — dramatic focus+context
          mat.opacity = 0.04
          mat.emissiveIntensity = 0.02
          group.scale.setScalar(0.85) // Shrink dimmed nodes
          if (glow) (glow.material as THREE.SpriteMaterial).opacity = 0.01
          if (label) (label.material as THREE.SpriteMaterial).opacity = 0.03
          if (ring) (ring.material as THREE.SpriteMaterial).opacity = 0
        }
      } else if (selectedNode && nodeId === selectedNode.id) {
        mat.opacity = 1
        mat.emissiveIntensity = 0.9
        group.scale.setScalar(1.2)
        if (glow) (glow.material as THREE.SpriteMaterial).opacity = 0.9
        if (label) (label.material as THREE.SpriteMaterial).opacity = 1
        if (ring) (ring.material as THREE.SpriteMaterial).opacity = 0.4
      } else {
        // Default state
        mat.opacity = 1
        mat.emissiveIntensity = nodeType === 'vc' ? 0.5 : 0.35
        group.scale.setScalar(1.0)
        if (glow) (glow.material as THREE.SpriteMaterial).opacity = nodeType === 'vc' ? 0.6 : 0.4
        if (label) (label.material as THREE.SpriteMaterial).opacity = 0.9
        if (ring) (ring.material as THREE.SpriteMaterial).opacity = 0.2
      }
    })
  }, [hoveredNode, selectedNode, highlightNodes])

  const handleNodeHover = useCallback((node: any, _prevNode: any) => {
    onNodeHover(node as GraphNode | null, null)
    // Change cursor
    const el = document.querySelector('.force-graph-container canvas') as HTMLCanvasElement | null
    if (el) el.style.cursor = node ? 'pointer' : 'default'
  }, [onNodeHover])

  const handleNodeClick = useCallback((node: any) => {
    onNodeClick(node as GraphNode)
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
        1200, // Slower, more cinematic fly-to (was 1000)
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
      backgroundColor="#F3EDE0"
      nodeId="id"
      nodeLabel=""
      nodeThreeObject={nodeThreeObject}
      nodeThreeObjectExtend={false}
      linkColor={(link: any) => {
        const l = link as GraphLink
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        const linkKey = `${sourceId}-${targetId}`

        if (hoveredNode) {
          if (highlightLinks.has(linkKey)) return '#B45309BB' // Brighter highlight links
          return '#B4530905' // More dramatic dimming
        }
        if (l.type === 'co-investor') return '#78716C' + (l.strength > 0.5 ? '38' : '20')
        return l.strength > 0.8 ? '#B4530940' : '#B4530922'
      }}
      linkWidth={(link: any) => {
        const l = link as GraphLink
        const sourceId = typeof l.source === 'object' ? (l.source as any).id : l.source
        const targetId = typeof l.target === 'object' ? (l.target as any).id : l.target
        const linkKey = `${sourceId}-${targetId}`

        if (hoveredNode && highlightLinks.has(linkKey)) return 3.5
        if (l.type === 'co-investor') return 0.5
        return l.strength > 0.8 ? 1.5 : 0.7
      }}
      linkOpacity={0.6}
      linkDirectionalParticles={(link: any) => {
        const l = link as GraphLink
        if (l.type !== 'investment') return 0
        // More particles for a richer feel
        return l.strength > 0.8 ? 3 : l.strength > 0.5 ? 2 : 1
      }}
      linkDirectionalParticleWidth={(link: any) => {
        const l = link as GraphLink
        // Larger, brighter particles
        return l.strength > 0.8 ? 2.5 : 1.8
      }}
      linkDirectionalParticleSpeed={(link: any) => {
        // Randomized speeds for organic feel
        const l = link as GraphLink
        const base = l.strength > 0.8 ? 0.004 : 0.003
        return base + Math.random() * 0.002
      }}
      linkDirectionalParticleColor={() => '#D9770688'}
      onNodeHover={handleNodeHover}
      onNodeClick={handleNodeClick}
      warmupTicks={FORCE_CONFIG.warmupTicks}
      cooldownTime={3000}
      enableNodeDrag={true}
      enableNavigationControls={true}
      showNavInfo={false}
      onEngineStop={handleEngineStop}
    />
  )
}
