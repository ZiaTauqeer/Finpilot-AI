/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Manrope', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 14px 36px rgba(17, 24, 39, 0.18)',
      },
      colors: {
        ink: '#0f172a',
        skyline: '#e2f3ff',
        mint: '#dcfce7',
        coral: '#fee2e2',
        ambersoft: '#fef3c7',
      },
    },
  },
  plugins: [],
}

