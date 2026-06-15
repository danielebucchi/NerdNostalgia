import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        retro: {
          bg: "#0d0221",
          panel: "#1a0633",
          accent: "#ff1f87",
          neon: "#00f0ff",
          sun: "#ffe66d",
          green: "#7cff6b",
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', "ui-monospace", "monospace"],
        retro: ['"VT323"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        pixel: "4px 4px 0 0 rgba(0,0,0,0.8)",
        neon: "0 0 12px rgba(0,240,255,0.6), 0 0 32px rgba(255,31,135,0.4)",
      },
    },
  },
  plugins: [],
};

export default config;
