import type { GraphNode, GraphLink } from './graph-types'

export function getForceConfig(nodeCount: number) {
  // Scale simulation parameters based on graph size
  const isLarge = nodeCount > 1000
  const isHuge = nodeCount > 3000

  return {
    charge: {
      strength: (node: GraphNode) => {
        if (node.type === 'vc') return isHuge ? -150 : isLarge ? -200 : -300
        return isHuge ? -30 : isLarge ? -50 : -100
      },
      distanceMax: isHuge ? 300 : isLarge ? 400 : 500,
    },

    link: {
      distance: (link: GraphLink) => {
        if (link.type === 'investment') return link.strength > 0.8 ? 40 : 80
        if (link.type === 'co-investor') return 120 - link.strength * 80
        return 100
      },
      strength: (link: GraphLink) => link.strength * (isHuge ? 0.3 : 0.5),
    },

    center: { strength: isHuge ? 0.08 : 0.05 },

    collision: {
      radius: (node: GraphNode) => node.size + (isLarge ? 3 : 5),
      strength: 0.7,
    },

    // Fewer warmup ticks for large graphs — faster initial render
    warmupTicks: isHuge ? 100 : isLarge ? 150 : 300,
    cooldownTime: isHuge ? 2000 : 3000,
  }
}

// Legacy export for backward compat
export const FORCE_CONFIG = getForceConfig(500)
