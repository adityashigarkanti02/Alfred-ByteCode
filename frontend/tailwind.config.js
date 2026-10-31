/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#0A0D14", // Deep void charcoal
          sidebar: "#0D111A", // Deep navy sidebar
          card: "#121824", // Raised dark navy card
          cardHover: "#182030",
          border: "#1E293B", // Subtle slate border
          accent: "#3B82F6", // Security blue
          accentGlow: "rgba(59, 130, 246, 0.15)",
          permitted: "#10B981", // Emerald green
          blocked: "#EF4444", // Crimson red
          warning: "#F59E0B", // Amber gold
          textPrimary: "#F8FAFC",
          textSecondary: "#94A3B8",
          textMuted: "#64748B",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "Courier New", "monospace"],
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
