import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  subtitle?: string
  icon?: LucideIcon
  trend?: { value: number; label: string }
  className?: string
}

export function StatCard({ label, value, subtitle, icon: Icon, trend, className }: StatCardProps) {
  return (
    <div className={cn('stat-card group', className)}>
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
          {label}
        </span>
        {Icon && (
          <div className="p-1.5 rounded-lg bg-indigo/10 text-indigo-light group-hover:bg-indigo/20 transition-colors">
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-bold text-text-primary font-mono tracking-tight">
          {value}
        </span>
        {subtitle && (
          <span className="text-sm text-text-secondary">{subtitle}</span>
        )}
      </div>
      {trend && (
        <div className={cn(
          'text-xs font-medium',
          trend.value > 0 ? 'text-emerald' : trend.value < 0 ? 'text-rose' : 'text-text-muted'
        )}>
          {trend.value > 0 ? '+' : ''}{trend.value}% {trend.label}
        </div>
      )}
    </div>
  )
}
