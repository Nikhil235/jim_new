/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0a0e1a',
        'bg-secondary': '#111827',
        'bg-card': '#1a1f35',
        'bg-card-hover': '#222842',
        'bg-sidebar': '#0d1225',
        'bg-input': '#1e2540',
        'gold-primary': '#f0b90b',
        'gold-secondary': '#d4a20a',
      }
    },
  },
  plugins: [],
}
