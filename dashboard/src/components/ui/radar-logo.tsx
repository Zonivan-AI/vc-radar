'use client'

import { cn } from '@/lib/utils'

interface RadarLogoProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  animate?: boolean
}

const sizes = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-14 h-14',
}

const svgSizes = {
  sm: 18,
  md: 22,
  lg: 30,
}

/**
 * VC Radar logo — a radar sweep icon with concentric arcs and a sweep line.
 * Dark background (#292524) with amber accent (#D4A843).
 */
export function RadarLogo({ size = 'sm', className, animate = false }: RadarLogoProps) {
  const s = svgSizes[size]

  return (
    <div
      className={cn(
        sizes[size],
        'rounded-lg flex items-center justify-center flex-shrink-0',
        className,
      )}
      style={{ background: '#292524' }}
    >
      <svg
        width={s}
        height={s}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Outer arc */}
        <path
          d="M12 2C6.48 2 2 6.48 2 12"
          stroke="#D4A843"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.35"
        />
        {/* Middle arc */}
        <path
          d="M12 6C8.69 6 6 8.69 6 12"
          stroke="#D4A843"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.55"
        />
        {/* Inner arc */}
        <path
          d="M12 10C10.9 10 10 10.9 10 12"
          stroke="#D4A843"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.8"
        />
        {/* Center dot */}
        <circle cx="12" cy="12" r="1.8" fill="#D4A843" />
        {/* Sweep line */}
        <line
          x1="12"
          y1="12"
          x2="12"
          y2="3"
          stroke="#D4A843"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.9"
        >
          {animate && (
            <animateTransform
              attributeName="transform"
              type="rotate"
              from="0 12 12"
              to="360 12 12"
              dur="3s"
              repeatCount="indefinite"
            />
          )}
        </line>
        {/* Blip dots — representing detected VCs */}
        <circle cx="8" cy="5.5" r="1" fill="#D4A843" opacity="0.7" />
        <circle cx="4.5" cy="10" r="0.8" fill="#D4A843" opacity="0.5" />
        <circle cx="17" cy="8" r="0.9" fill="#D4A843" opacity="0.4" />
      </svg>
    </div>
  )
}
