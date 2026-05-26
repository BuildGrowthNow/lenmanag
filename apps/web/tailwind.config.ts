import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "hsl(var(--bg))",
        panel: "hsl(var(--panel))",
        "panel-2": "hsl(var(--panel-2))",
        line: "hsl(var(--line))",
        text: "hsl(var(--text))",
        muted: "hsl(var(--muted))",
        accent: "hsl(var(--accent))",
        accentText: "hsl(var(--accent-text))",
        danger: "hsl(var(--danger))",
        warning: "hsl(var(--warning))",
        success: "hsl(var(--success))"
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,255,255,0.03), 0 24px 80px rgba(0,0,0,0.45)"
      },
      backgroundImage: {
        "shell-grid":
          "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
        "shell-radial":
          "radial-gradient(circle at top, rgba(227, 160, 62, 0.18), transparent 34%), radial-gradient(circle at right, rgba(255,255,255,0.07), transparent 24%)"
      }
    }
  },
  plugins: []
};

export default config;
