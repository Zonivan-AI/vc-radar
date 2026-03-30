import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number | null | undefined): string {
  if (amount == null) return 'N/A'
  if (amount >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`
  return `$${amount}`
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return 'N/A'
  return n.toLocaleString()
}

export function generateSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim()
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'Active': return 'text-emerald bg-emerald/10'
    case 'Acquired': return 'text-amber bg-amber/10'
    case 'IPO': return 'text-accent bg-accent/10'
    case 'Shutdown': return 'text-rose bg-rose/10'
    default: return 'text-text-secondary bg-white/5'
  }
}

export function getConfidenceColor(confidence: string): string {
  switch (confidence) {
    case 'High': return 'text-emerald'
    case 'Medium': return 'text-amber'
    case 'Low': return 'text-rose'
    default: return 'text-text-muted'
  }
}

export function getSectorColor(sector: string): string {
  const sectorLower = sector.toLowerCase()
  if (sectorLower.includes('infra') || sectorLower.includes('cloud')) return '#D97706'
  if (sectorLower.includes('security') || sectorLower.includes('cyber')) return '#F59E0B'
  if (sectorLower.includes('health') || sectorLower.includes('bio')) return '#EC4899'
  if (sectorLower.includes('fintech') || sectorLower.includes('finance')) return '#3B82F6'
  if (sectorLower.includes('robot') || sectorLower.includes('auto')) return '#8B5CF6'
  if (sectorLower.includes('dev') || sectorLower.includes('tool') || sectorLower.includes('code')) return '#14B8A6'
  if (sectorLower.includes('consumer') || sectorLower.includes('social')) return '#F97316'
  return '#10B981' // AI Apps / default
}

export const SECTOR_COLORS: Record<string, string> = {
  'AI Infra': '#D97706',
  'AI Apps': '#10B981',
  'Security': '#F59E0B',
  'Healthcare': '#EC4899',
  'Fintech': '#3B82F6',
  'Robotics': '#8B5CF6',
  'Dev Tools': '#14B8A6',
  'Consumer': '#F97316',
}

export const CHART_COLORS = [
  '#D97706', '#10B981', '#F59E0B', '#EC4899',
  '#3B82F6', '#8B5CF6', '#14B8A6', '#F97316',
]
