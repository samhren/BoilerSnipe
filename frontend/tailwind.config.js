/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'purdue-gold': '#CFB991',
        'purdue-black': '#000000',
      }
    },
  },
  plugins: [],
}
