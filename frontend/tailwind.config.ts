import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        // Palette dal logo NerdNostalgia (pastello, kawaii)
        cream: "#fff7ed",
        ink: {
          DEFAULT: "#3d2a5c",
          soft: "#6b5b8a",
          mute: "#9b8db8",
        },
        pink: {
          DEFAULT: "#f8a8c8",
          deep: "#e879a8",
          soft: "#fce4ee",
        },
        mint: {
          DEFAULT: "#a8e6d4",
          deep: "#7dd1b8",
          soft: "#e0f5ec",
        },
        sky: {
          DEFAULT: "#b8e0e8",
          deep: "#8ec5d8",
          soft: "#e6f3f7",
        },
        lilac: {
          DEFAULT: "#d4c4f0",
          deep: "#a890d8",
          soft: "#efe9fa",
        },
        star: "#fff4a8",
      },
      fontFamily: {
        display: ['"Fredoka"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Manrope"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        chonk: "28px",
        big: "22px",
      },
      boxShadow: {
        soft: "0 18px 40px -18px rgba(61, 42, 92, 0.25)",
        pop: "0 8px 0 0 rgba(61, 42, 92, 0.12)",
        hover: "0 22px 50px -16px rgba(232, 121, 168, 0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
