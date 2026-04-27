import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        /* ── Background scale ───────────────────────────────────────── */
        navy: {
          DEFAULT: "#000000", /* pure black page bg      */
          800:     "#0B0B0F", /* sidebar bg              */
          700:     "#1C1C1E", /* card bg                 */
          600:     "#2C2C2E", /* elevated card / hover   */
          500:     "#3A3A3C", /* input / control         */
          400:     "#48484A", /* separator               */
        },
        /* ── Accent colours (Apple system palette) ─────────────────── */
        cyan: {
          DEFAULT: "#0A84FF",
          dim:     "#0066CC",
          glow:    "rgba(10,132,255,0.12)",
        },
        pink: {
          DEFAULT: "#FF2D55",
          dim:     "#CC2444",
        },
        green: {
          DEFAULT: "#32D74B",
          dim:     "#1E8A2E",
          glow:    "rgba(50,215,75,0.12)",
        },
        amber: {
          DEFAULT: "#FF9F0A",
          dim:     "#C57A07",
          glow:    "rgba(255,159,10,0.12)",
        },
        red: {
          DEFAULT: "#FF453A",
          dim:     "#B82E25",
          glow:    "rgba(255,69,58,0.12)",
        },
        /* ── Glass surface ─────────────────────────────────────────── */
        glass: {
          DEFAULT: "rgba(17,17,19,0.95)",
          light:   "rgba(28,28,30,0.80)",
          border:  "rgba(84,84,88,0.35)",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SF Mono", "Consolas", "monospace"],
        display: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
      boxShadow: {
        glass:
          "0 2px 20px rgba(0,0,0,0.65), inset 0 0.5px 0 rgba(255,255,255,0.05)",
        "glass-lg":
          "0 8px 40px rgba(0,0,0,0.75), inset 0 0.5px 0 rgba(255,255,255,0.06)",
        "card-hover":
          "0 4px 24px rgba(0,0,0,0.55)",
      },
      animation: {
        "pulse-glow":     "pulseGlow 3s ease-in-out infinite",
        "fade-in":        "fadeIn 0.35s ease-out",
        "slide-up":       "slideUp 0.4s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "0.5" },
          "50%":      { opacity: "1"   },
        },
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to:   { opacity: "1", transform: "translateY(0)"    },
        },
        slideInRight: {
          from: { opacity: "0", transform: "translateX(14px)" },
          to:   { opacity: "1", transform: "translateX(0)"    },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};

export default config;
