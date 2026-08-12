import type { Config } from "tailwindcss";

// Section 5.1 theme tokens - overrides Tailwind's default palette rather
// than extending it, per the "Industrial Medical-Grade AOI Console" spec.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#FFFFFF",
      black: "#000000",
      bg: {
        primary: "#0A0C0F",
        secondary: "#111418",
        tertiary: "#1A1F26",
        terminal: "#050709",
      },
      border: {
        DEFAULT: "#252C36",
      },
      accent: {
        cyan: "#00D4FF",
        amber: "#FFB020",
        crimson: "#FF3B3B",
        green: "#00E676",
        purple: "#9B6DFF",
      },
      text: {
        primary: "#E8EDF5",
        secondary: "#8896A8",
        muted: "#4A5568",
      },
      defect: {
        open: "#2979FF",
        short: "#FF3B3B",
        mousebite: "#FF6EC7",
        spur: "#FFB020",
        copper: "#FF6D00",
        pinhole: "#00E676",
        missinghole: "#9B6DFF",
      },
      severity: {
        critical: "#FF3B3B",
        major: "#FFB020",
        minor: "#00E676",
      },
      termgreen: "#00FF88",
    },
    fontFamily: {
      mono: ["'JetBrains Mono'", "monospace"],
      sans: ["'IBM Plex Sans'", "sans-serif"],
      code: ["'Fira Code'", "monospace"],
    },
    extend: {
      borderRadius: {
        industrial: "4px",
        btn: "2px",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
