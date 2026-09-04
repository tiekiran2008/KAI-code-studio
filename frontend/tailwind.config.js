/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#090d16',
          paper: '#0f172a',
          card: '#1e293b',
        },
        border: {
          DEFAULT: 'rgba(255, 255, 255, 0.08)',
          glow: 'rgba(99, 102, 241, 0.3)',
        },
        accent: {
          blue: '#3b82f6',
          indigo: '#6366f1',
          purple: '#a855f7',
          cyan: '#06b6d4',
          emerald: '#10b981',
          rose: '#f43f5e',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px -5px rgba(99, 102, 241, 0.4)',
        'glow-cyan': '0 0 20px -5px rgba(6, 182, 212, 0.4)',
      }
    },
  },
  plugins: [],
}
