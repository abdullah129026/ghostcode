import type { Config } from "tailwindcss";

// GhostCode design tokens (law): light editorial dev-tool. Paper-white
// surfaces, deep slate text, one terminal-emerald accent, danger red only
// for destructive actions. Inter for UI, JetBrains Mono for code and money.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FDFCFB",
        ink: {
          DEFAULT: "#1C1917",
          soft: "#57534E",
        },
        line: "#E7E5E4",
        moss: {
          DEFAULT: "#059669",
          deep: "#047857",
        },
        clay: "#DC2626",
        amber: "#D97706",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
