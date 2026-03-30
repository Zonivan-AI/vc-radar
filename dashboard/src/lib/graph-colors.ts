// ============================================================================
// VC Radar — Sector-based color system for graph nodes
// ============================================================================

// Sector → color mapping (vibrant but cohesive palette)
const SECTOR_COLORS: Record<string, string> = {
  // Technology & Software
  'AI':               '#8B5CF6',  // violet
  'AI/ML':            '#8B5CF6',
  'Artificial Intelligence': '#8B5CF6',
  'Machine Learning': '#8B5CF6',
  'SaaS':             '#D97706',  // amber
  'Software':         '#D97706',
  'Enterprise':       '#D97706',
  'Enterprise Software': '#D97706',
  'Developer Tools':  '#14B8A6',  // teal
  'Dev Tools':        '#14B8A6',
  'DevOps':           '#14B8A6',
  'Infrastructure':   '#0EA5E9',  // sky
  'Cloud':            '#0EA5E9',
  'Data':             '#06B6D4',  // cyan
  'Analytics':        '#06B6D4',

  // Finance
  'Fintech':          '#3B82F6',  // blue
  'Financial Services': '#3B82F6',
  'Payments':         '#3B82F6',
  'Banking':          '#3B82F6',
  'Crypto':           '#F59E0B',  // amber
  'Blockchain':       '#F59E0B',
  'Web3':             '#F59E0B',
  'DeFi':             '#F59E0B',

  // Health
  'Healthcare':       '#EC4899',  // pink
  'Health':           '#EC4899',
  'Healthtech':       '#EC4899',
  'Biotech':          '#D946EF',  // fuchsia
  'Life Sciences':    '#D946EF',

  // Consumer
  'Consumer':         '#F97316',  // orange
  'E-commerce':       '#F97316',
  'Ecommerce':        '#F97316',
  'Marketplace':      '#FB923C',  // light orange
  'Social':           '#F43F5E',  // rose
  'Media':            '#F43F5E',
  'Gaming':           '#EF4444',  // red
  'Entertainment':    '#EF4444',
  'EdTech':           '#A78BFA',  // light violet
  'Education':        '#A78BFA',

  // Industrial & Hardware
  'Hardware':         '#78716C',  // stone
  'Robotics':         '#7C3AED',  // purple
  'Climate':          '#22C55E',  // green
  'CleanTech':        '#22C55E',
  'Energy':           '#22C55E',
  'Sustainability':   '#22C55E',
  'Food':             '#84CC16',  // lime
  'FoodTech':         '#84CC16',
  'AgTech':           '#84CC16',
  'Logistics':        '#64748B',  // slate
  'Supply Chain':     '#64748B',
  'Transportation':   '#64748B',
  'Real Estate':      '#0D9488',  // teal darker
  'PropTech':         '#0D9488',

  // Security
  'Security':         '#F59E0B',  // amber
  'Cybersecurity':    '#F59E0B',
}

// Fallback for unknown sectors — hash to a color
const FALLBACK_COLORS = [
  '#D97706', '#8B5CF6', '#EC4899', '#F43F5E',
  '#F97316', '#F59E0B', '#22C55E', '#14B8A6',
  '#06B6D4', '#3B82F6', '#A78BFA', '#D946EF',
]

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

export function getSectorColor(sector: string | null | undefined): string {
  if (!sector) return '#64748B'  // muted slate for unknown

  // Try exact match
  if (SECTOR_COLORS[sector]) return SECTOR_COLORS[sector]

  // Try case-insensitive partial match
  const lower = sector.toLowerCase()
  for (const [key, color] of Object.entries(SECTOR_COLORS)) {
    if (lower.includes(key.toLowerCase()) || key.toLowerCase().includes(lower)) {
      return color
    }
  }

  // Hash-based fallback
  return FALLBACK_COLORS[hashString(sector) % FALLBACK_COLORS.length]
}

// VC node gradient colors (amber spectrum)
export const VC_GRADIENT = {
  primary:   '#B45309',
  secondary: '#92400E',
  glow:      '#D97706',
  hover:     '#F59E0B',
  dimmed:    '#B453091F',
}

// Add a warm glow version (brighter, slightly transparent)
export function getGlowColor(baseColor: string): string {
  // Make the color warmer and brighter for glow effect
  return baseColor + 'B3'
}
