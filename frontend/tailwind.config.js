/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        // SkilTak Aurora sober palette — single source of truth.
        // Orange is the only brand color; the slate-blue cold accent
        // and the soft red ("danger zone") are intentionally rare and
        // only used where explicitly specified in mockups.
        canvas: '#0B0E14',
        'surface-1': '#11151D',
        'surface-2': '#161A24',
        'surface-3': '#1E2330',
        bone: '#E8E5DD',
        'warm-grey': '#8B8A85',
        dim: '#54534F',
        primary: {
          // SkilTak orange. `DEFAULT` lets templates write
          // `bg-primary` / `text-primary` (no shade) — used in 150+
          // places, so keep it even though it duplicates `500`.
          50: '#FFF6F0',
          100: '#FEEADC',
          200: '#FDD2B4',
          300: '#FBAB74',
          400: '#FA822E',
          500: '#F97316',
          600: '#E15F06',
          700: '#B94F05',
          800: '#913E04',
          900: '#6A2D03',
          DEFAULT: '#F97316',
        },
        'slate-accent': '#94A3B8',
        danger: '#EF6F6F',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        // Dramatic headline-to-body scale required by the sober brief.
        // Use `text-display` for the hero (88px), `text-display-md`
        // for section titles (56px), `text-headline` for subtitles.
        display: ['88px', { lineHeight: '1.05', letterSpacing: '-0.04em', fontWeight: '900' }],
        'display-md': ['56px', { lineHeight: '1.1', letterSpacing: '-0.03em', fontWeight: '900' }],
        headline: ['32px', { lineHeight: '1.25', letterSpacing: '-0.02em', fontWeight: '700' }],
        subhead: ['22px', { lineHeight: '1.4', letterSpacing: '-0.01em', fontWeight: '600' }],
        'body-lg': ['18px', { lineHeight: '1.6', fontWeight: '400' }],
        body: ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        label: ['12px', { lineHeight: '1.4', letterSpacing: '0.08em', fontWeight: '600' }],
        metric: ['14px', { lineHeight: '1.4', fontWeight: '500' }],
      },
      spacing: {
        gutter: '24px',
        'container-max': '1440px',
      },
      animation: {
        'fade-in': 'fadeIn 1000ms cubic-bezier(0.16, 1, 0.3, 1)',
        'float-slow': 'floatSlow 8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-12px)' },
        },
      },
      backdropBlur: {
        xs: '2px',
        sm: '4px',
        md: '8px',
        lg: '12px',
        xl: '20px',
      },
    },
  },
  plugins: [],
};
