import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // VC Radar — Meridian Design System (warm ivory / cartographer)
        background: '#FBF9F4',
        surface: {
          DEFAULT: '#FFFFFF',
          raised: '#F5F0E8',
        },
        border: '#E7E5E4',
        // Primary accent — amber
        accent: {
          DEFAULT: '#B45309',
          light: '#D97706',
          dark: '#92400E',
          glow: 'rgba(180, 83, 9, 0.15)',
        },
        // Node colors
        node: {
          vc: '#B45309',
          company: '#78716C',
          'company-hover': '#57534E',
          'vc-hover': '#D97706',
        },
        // Legacy accent colors (for dashboard pages)
        indigo: {
          DEFAULT: '#B45309',
          light: '#D97706',
          dark: '#92400E',
        },
        emerald: {
          DEFAULT: '#10B981',
          light: '#34D399',
        },
        amber: {
          DEFAULT: '#F59E0B',
          light: '#FBBF24',
        },
        rose: {
          DEFAULT: '#F43F5E',
          light: '#FB7185',
        },
        // Text — warm stone tones
        'text-primary': '#292524',
        'text-secondary': '#78716C',
        'text-muted': '#A8A29E',
        // Glass panel
        glass: {
          bg: 'rgba(255, 255, 255, 0.45)',
          border: 'rgba(180, 165, 140, 0.12)',
        },
        // Chart palette (for dashboard pages)
        chart: {
          'ai-infra': '#6366F1',
          'ai-apps': '#10B981',
          'security': '#F59E0B',
          'healthcare': '#EC4899',
          'fintech': '#3B82F6',
          'robotics': '#8B5CF6',
          'dev-tools': '#14B8A6',
          'consumer': '#F97316',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['IBM Plex Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'glass': 'linear-gradient(135deg, rgba(255,255,255,0.50) 0%, rgba(255,255,255,0.30) 100%)',
        'glass-hover': 'linear-gradient(135deg, rgba(255,255,255,0.60) 0%, rgba(255,255,255,0.40) 100%)',
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(180, 165, 140, 0.10), inset 0 0 0 1px rgba(180, 165, 140, 0.06)',
        'glass-strong': '0 12px 48px rgba(180, 165, 140, 0.14), inset 0 0 0 1px rgba(180, 165, 140, 0.08)',
        'glow-accent': '0 0 24px rgba(180, 83, 9, 0.15)',
        'glow-indigo': '0 0 20px rgba(180, 83, 9, 0.12)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.15)',
        'input-focus': '0 0 0 3px rgba(180, 83, 9, 0.10), 0 0 16px rgba(180, 83, 9, 0.06)',
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'breathe': 'breathe 3s ease-in-out infinite',
        'scale-in': 'scaleIn 0.2s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
}

export default config
