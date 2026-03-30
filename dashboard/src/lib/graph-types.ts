import type { VCFirm, Company } from './types'

export interface GraphNode {
  id: string
  type: 'vc' | 'company'
  name: string
  size: number
  color: string
  glowColor?: string
  sector?: string
  data: VCFirm | Company
  // d3-force mutable properties
  x?: number
  y?: number
  z?: number
  fx?: number
  fy?: number
  fz?: number
}

export interface GraphLink {
  source: string
  target: string
  type: 'investment' | 'co-investor'
  strength: number
  label?: string
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface GraphFilters {
  showVCs: boolean
  showCompanies: boolean
  sectors: string[]
  searchQuery: string
}
