/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Deep ink base - an agentic finance cockpit, not a generic admin
        ink: {
          950: '#05080F',
          900: '#070B14',
          850: '#0B1120',
          800: '#0E1526',
          700: '#141D33',
          600: '#1C2844'
        },
        // PayPal-family electric blue
        bolt: {
          DEFAULT: '#2E7CFF',
          soft: '#5C9BFF',
          deep: '#1B5BD6',
          dim: '#173B70'
        },
        // The "spark" - money saved, energy released
        spark: {
          DEFAULT: '#FFB224',
          soft: '#FFC961',
          dim: '#4A3708'
        },
        mint: { DEFAULT: '#34D399', dim: '#0C2B1F' },
        coral: { DEFAULT: '#F87171', dim: '#3B1516' },
        fog: {
          DEFAULT: '#8B96AB',
          bright: '#E8EDF6',
          dim: '#5A6478'
        },
        hairline: 'rgba(148, 163, 184, 0.12)'
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace']
      },
      boxShadow: {
        panel: '0 1px 0 rgba(148,163,184,0.06) inset',
        lift: '0 8px 24px rgba(3, 7, 18, 0.55)',
        spark: '0 0 0 1px rgba(255,178,36,0.35), 0 0 24px rgba(255,178,36,0.18)'
      },
      borderRadius: {
        xl: '14px'
      }
    }
  },
  plugins: []
}
