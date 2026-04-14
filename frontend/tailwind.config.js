/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        va: {
          blue: '#003DA5',
          red: '#C0272D',
          gold: '#F5A623',
        },
      },
    },
  },
  plugins: [],
}
