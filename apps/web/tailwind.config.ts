import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        streamwise: {
          bg: "#0f0f12",
          surface: "#1a1a22",
          accent: "#6366f1",
          muted: "#94a3b8",
        },
      },
    },
  },
  plugins: [],
};

export default config;
