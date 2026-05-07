/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/styles/globals.css',
    './src/styles/components.css',
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#021B2C',
          card: '#0A2E44',
          muted: '#0A2E44',
        },
        foreground: {
          DEFAULT: '#D6EAF0',
          muted: '#7FB3C8',
        },
        border: {
          DEFAULT: '#1C7293',
          input: 'rgba(255, 255, 255, 0.1)',
        },
      },
      fontFamily: {
        sans: ['Syne', 'DM Sans', 'DM Mono'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
