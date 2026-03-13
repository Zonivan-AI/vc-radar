import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Meridian Design System
        background: '#0A0F1E',
        surface: {
          DEFAULT: '#111827',
          raised: '#1A2235',
        },
        border: '#1F2937',
        // Accent colors
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
        // Text
        'text-primary': '#F9FAFB',
        'text-secondary': '#9CA3AF',
        'text-muted': '#4B5563',
        // Chart palette
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
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glow-indigo': '0 0 20px rgba(99, 102, 241, 0.15)',
        'glow-emerald': '0 0 20px rgba(16, 185, 129, 0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
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
      },
    },
  },
  plugins: [],
}

export default config
