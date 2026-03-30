/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#6C63FF", dark: "#5A54E0", light: "#8B85FF" },
        surface: { DEFAULT: "#0F0F1A", card: "#16162A", border: "#2A2A45" },
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
