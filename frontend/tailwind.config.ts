import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#14110e",
        panel: "#1c1814",
        card: "#241f1a",
        line: "#3a3229",
        cream: "#f3ebe0",
        mute: "#9a8f82",
        gold: "#f0a202",
        rust: "#c44900",
        river: "#3d8b8b",
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
