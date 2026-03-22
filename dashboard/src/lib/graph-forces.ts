import type { GraphNode, GraphLink } from './graph-types'

export const FORCE_CONFIG = {
  charge: {
    strength: (node: GraphNode) => {
      if (node.type === 'vc') return -300
      return -100
    },
    distanceMax: 500,
  },

  link: {
    distance: (link: GraphLink) => {
      if (link.type === 'investment') return link.strength > 0.8 ? 40 : 80
      if (link.type === 'co-investor') return 120 - link.strength * 80
      return 100
    },
    strength: (link: GraphLink) => link.strength * 0.5,
  },

  center: { strength: 0.05 },

  collision: {
    radius: (node: GraphNode) => node.size + 5,
    strength: 0.7,
  },

  warmupTicks: 300,
}
