'use client'

import { cn } from '@/lib/utils'

interface HeatmapCell {
  vcName: string
  sector: string
  count: number
}

interface InvestmentHeatmapProps {
  data: HeatmapCell[]
  vcNames: string[]
  sectors: string[]
}

function getHeatColor(count: number, max: number): string {
  if (count === 0) return 'bg-white/[0.02]'
  const intensity = count / max
  if (intensity > 0.7) return 'bg-indigo/60'
  if (intensity > 0.4) return 'bg-indigo/35'
  if (intensity > 0.2) return 'bg-indigo/20'
  return 'bg-indigo/10'
}

export function InvestmentHeatmap({ data, vcNames, sectors }: InvestmentHeatmapProps) {
  const cellMap = new Map<string, number>()
  let maxCount = 0
  data.forEach(cell => {
    const key = `${cell.vcName}|${cell.sector}`
    cellMap.set(key, cell.count)
    if (cell.count > maxCount) maxCount = cell.count
  })

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left py-2 px-2 text-text-muted font-medium w-32">VC Firm</th>
            {sectors.map(s => (
              <th key={s} className="text-center py-2 px-1 text-text-muted font-medium min-w-[60px]">
                <span className="truncate block max-w-[60px]" title={s}>
                  {s.split('/')[0].split(' ')[0]}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {vcNames.map(vc => (
            <tr key={vc} className="group">
              <td className="py-1 px-2 text-text-secondary font-medium truncate max-w-[120px]" title={vc}>
                {vc}
              </td>
              {sectors.map(sector => {
                const count = cellMap.get(`${vc}|${sector}`) ?? 0
                return (
                  <td key={sector} className="py-1 px-1">
                    <div
                      className={cn(
                        'w-full h-7 rounded flex items-center justify-center transition-all',
                        getHeatColor(count, maxCount),
                        count > 0 && 'hover:ring-1 hover:ring-indigo/50 cursor-default'
                      )}
                      title={`${vc}: ${count} investments in ${sector}`}
                    >
                      {count > 0 && (
                        <span className="text-[10px] font-mono text-text-primary/70">
                          {count}
                        </span>
                      )}
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
