/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Lumen · Night Foundry — values mirror tokens.css (kept literal so
        // Tailwind alpha modifiers like bg-brass/10 compile)
        paper: "oklch(12.5% 0.013 272 / <alpha-value>)",
        paper2: "oklch(16% 0.015 272 / <alpha-value>)",
        paper3: "oklch(20.5% 0.017 272 / <alpha-value>)",
        ink: "oklch(97% 0.005 272 / <alpha-value>)",
        ink2: "oklch(87% 0.009 272 / <alpha-value>)",
        muted: "oklch(67% 0.014 272 / <alpha-value>)",
        brass: "oklch(66% 0.2 285 / <alpha-value>)",
        brassink: "oklch(98% 0.01 285 / <alpha-value>)",
        coral: "oklch(72% 0.14 225 / <alpha-value>)",
        ok: "oklch(77% 0.15 162 / <alpha-value>)",
        warn: "oklch(80% 0.15 80 / <alpha-value>)",
        danger: "oklch(67% 0.2 22 / <alpha-value>)",
        // legacy aliases so untouched files degrade gracefully
        background: "oklch(12.5% 0.013 272 / <alpha-value>)",
        surface: "oklch(16% 0.015 272 / <alpha-value>)",
        primary: "oklch(66% 0.2 285 / <alpha-value>)",
        accent: "oklch(72% 0.14 225 / <alpha-value>)",
      },
      fontFamily: {
        display: "var(--font-display)",
        body: "var(--font-body)",
        sans: "var(--font-body)",
        serif: "var(--font-display)",
        mono: "var(--font-mono)",
      },
      borderColor: {
        rule: "var(--color-rule)",
        rule2: "var(--color-rule-2)",
      },
      borderRadius: {
        card: "var(--radius-card)",
        input: "var(--radius-input)",
      },
      fontSize: {
        micro: ["10.5px", { letterSpacing: "0.10em" }],
      },
      transitionTimingFunction: {
        out: "var(--ease-out)",
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade': 'fadeIn 0.4s var(--ease-out)',
        // mobile shell: the nav drawer flies in from the edge, sheets rise
        'slide-in-left': 'slideInLeft 0.24s var(--ease-out)',
        'sheet-up': 'sheetUp 0.26s var(--ease-out)',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideInLeft: {
          from: { transform: 'translateX(-100%)' },
          to: { transform: 'translateX(0)' },
        },
        sheetUp: {
          from: { transform: 'translateY(12px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
