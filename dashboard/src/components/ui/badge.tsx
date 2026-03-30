import { cn } from '@/lib/utils'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'accent' | 'emerald' | 'amber' | 'rose'
  className?: string
}

const variants = {
  default: 'bg-white/5 text-text-secondary',
  accent: 'bg-accent/10 text-accent',
  emerald: 'bg-emerald/10 text-emerald',
  amber: 'bg-amber/10 text-amber',
  rose: 'bg-rose/10 text-rose',
}

export function Badge({ children, variant = 'default', className }: BadgeProps) {
  return (
    <span className={cn('badge', variants[variant], className)}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const variant = {
    Active: 'emerald' as const,
    Acquired: 'amber' as const,
    IPO: 'accent' as const,
    Shutdown: 'rose' as const,
  }[status] ?? 'default' as const

  return <Badge variant={variant}>{status}</Badge>
}

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const variant = {
    High: 'emerald' as const,
    Medium: 'amber' as const,
    Low: 'rose' as const,
  }[confidence] ?? 'default' as const

  return <Badge variant={variant}>{confidence}</Badge>
}
