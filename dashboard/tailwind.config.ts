import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // VC Radar Design System
        background: '#060A14',
        surface: {
          DEFAULT: '#0F172B',
          raised: '#1A2235',
        },
        border: '#1E293B',
        // Primary accent — periwinkle blue
        accent: {
          DEFAULT: '#7C8FFF',
          light: '#A5B4FC',
          dark: '#6366F1',
          glow: 'rgba(124, 143, 255, 0.20)',
        },
        // Node colors
        node: {
          vc: '#7C8FFF',
          company: '#38BDF8',
          'company-hover': '#67E8F9',
          'vc-hover': '#A5B4FC',
        },
        // Legacy accent colors (for dashboard pages)
        indigo: {
          DEFAULT: '#6366F1',
          light: '#818CF8',
          dark: '#4F46E5',
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
        // Text — warmer slate tones
        'text-primary': '#E2E8F0',
        'text-secondary': '#94A3B8',
        'text-muted': '#475569',
        // Glass panel
        glass: {
          bg: 'rgba(15, 23, 42, 0.75)',
          border: 'rgba(148, 163, 184, 0.08)',
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
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'glass': 'linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
        'glass-hover': 'linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.04) 100%)',
        'gradient-radial': 'radial-gradient(ellipse at center, var(--tw-gradient-stops))',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 0 0 1px rgba(148, 163, 184, 0.05)',
        'glass-strong': '0 12px 48px rgba(0, 0, 0, 0.5), inset 0 0 0 1px rgba(148, 163, 184, 0.06)',
        'glow-accent': '0 0 24px rgba(124, 143, 255, 0.15)',
        'glow-indigo': '0 0 20px rgba(99, 102, 241, 0.15)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.15)',
        'input-focus': '0 0 0 3px rgba(124, 143, 255, 0.12), 0 0 16px rgba(124, 143, 255, 0.08)',
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
