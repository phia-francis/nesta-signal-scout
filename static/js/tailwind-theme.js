/**
 * static/js/tailwind-theme.js
 *
 * Nesta Visual Identity (v2.0)
 * - Core electric blue + primary/secondary palette
 * - Neutral black/white support
 */

tailwind.config = {
  theme: {
    extend: {
      colors: {
        nesta: {
          // Core colour
          blue: '#0000FF',

          // Primary palette
          navy: '#0F294A',
          green: '#18A48C',
          purple: '#9A1BBE',
          red: '#EB003B',
          pink: '#F6A4B7',
          yellow: '#FDB633',

          // Secondary palette
          aqua: '#97D9E3',
          violet: '#A59BEE',
          orange: '#FF6E47',
          'dark-grey': '#646363',
          sand: '#D2C9C0',

          // Neutrals
          black: '#000000',
          white: '#FFFFFF',
        },
      },
      fontFamily: {
        sans: ['Averta', 'Inter', 'sans-serif'],
        display: ['Zosia', 'Georgia', 'serif'],
        body: ['Averta', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        hard: '4px 4px 0px 0px rgba(0, 0, 0, 0.1)',
      },
      animation: {
        'slide-in': 'fadeInUp 0.5s ease-out forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
};
