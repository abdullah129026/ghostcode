import type { Config } from "tailwindcss";

// GhostCode design tokens. Living Design Copy system (spacing, type scale,
// radius, shadow, motion) with GhostCode's own palette: warm paper ground,
// deep ink text, spectral violet accent (dead code into a P&L statement,
// not the copy's emerald). Solid colors only, never gradients. Every color
// is a CSS variable so light and dark are token-for-token mirrors.
// Inter for UI, JetBrains Mono for code and money.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: "rgb(var(--bg) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        "surface-2": "rgb(var(--surface-2) / <alpha-value>)",
        ink: {
          DEFAULT: "rgb(var(--ink) / <alpha-value>)",
          soft: "rgb(var(--ink-soft) / <alpha-value>)",
        },
        "ink-2": "rgb(var(--ink-2) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        line: {
          DEFAULT: "rgb(var(--line) / <alpha-value>)",
          2: "rgb(var(--line-2) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent) / <alpha-value>)",
          deep: "rgb(var(--accent-deep) / <alpha-value>)",
          tint: "rgb(var(--accent-tint) / <alpha-value>)",
          soft: "rgb(var(--accent-soft) / <alpha-value>)",
        },
        "on-accent": "rgb(var(--accent-fg) / <alpha-value>)",
        "on-danger": "rgb(var(--danger-fg) / <alpha-value>)",
        clay: "rgb(var(--red) / <alpha-value>)",
        amber: "rgb(var(--amber) / <alpha-value>)",
        info: "rgb(var(--blue) / <alpha-value>)",
        teal: "rgb(var(--teal) / <alpha-value>)",
        violet: "rgb(var(--accent) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },
      // Living Design Copy type scale. No sizes between steps.
      fontSize: {
        display: ["48px", { lineHeight: "1.05", fontWeight: "700" }],
        h1: ["32px", { lineHeight: "1.12", fontWeight: "700" }],
        h2: ["24px", { lineHeight: "1.2", fontWeight: "700" }],
        h3: ["18px", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["16px", { lineHeight: "1.55", fontWeight: "400" }],
        "body-sm": ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        caption: ["12px", { lineHeight: "1.4", fontWeight: "500" }],
        overline: [
          "11px",
          { lineHeight: "1.3", fontWeight: "700", letterSpacing: "0.18em" },
        ],
      },
      borderRadius: {
        sm: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
      boxShadow: {
        sm: "0 1px 2px rgb(var(--ink) / 0.06)",
        md: "0 4px 16px rgb(var(--ink) / 0.10)",
        lg: "0 12px 32px rgb(var(--ink) / 0.16)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fade-up 600ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in": "fade-in 200ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
      transitionTimingFunction: {
        "ease-out": "cubic-bezier(0.16, 1, 0.3, 1)",
        "ease-in-out": "cubic-bezier(0.65, 0, 0.35, 1)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
