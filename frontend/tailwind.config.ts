import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#f6f1e6",
        panel: "#efe4d2",
        card: "#fffdf8",
        line: "#e2d5bf",
        cream: "#241f1a",
        mute: "#8a7d6c",
        gold: "#b9790a",
        rust: "#b23c00",
        river: "#2f6b6b",
        night: "#1c1814",
      },
      fontFamily: {
        display: ["var(--font-display)", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        lift: "0 18px 50px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
