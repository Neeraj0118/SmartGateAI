/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ivory:    '#F4F1EA',
        charcoal: '#252A2E',
        forest:   '#315C4A',
        sage:     '#DCE5DC',
        amber:    '#D58A36',
        muted:    '#737B78',
        errored:  '#B94A48',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.07), 0 1px 2px rgba(0,0,0,0.05)',
        elevated: '0 4px 16px rgba(0,0,0,0.10)',
      },
    },
  },
  plugins: [],
}
