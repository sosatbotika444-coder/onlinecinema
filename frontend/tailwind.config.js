/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "sans-serif"]
      },
      boxShadow: {
        neon: "0 0 32px rgba(255, 45, 149, 0.38)",
        glass: "0 18px 80px rgba(0, 0, 0, 0.42)"
      }
    }
  },
  plugins: []
};
