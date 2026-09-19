import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Ledger green: a finance identity, used sparingly for primary actions.
        primary: {
          DEFAULT: "#166534", // green-800
          hover: "#14532d", // green-900
        },
        background: "#f7f7f5", // warm off-white page background
        surface: "#ffffff",
        border: "#e5e5e2",
        foreground: "#1c1917", // stone-900
        muted: "#78716c", // stone-500
        subtle: "#a8a29e", // stone-400
        success: "#15803d", // green-700
        warning: "#b45309", // amber-700
        error: "#b91c1c", // red-700
        info: "#1d4ed8", // blue-700
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      maxWidth: {
        page: "1120px",
      },
      borderRadius: {
        // Restrained radius system: no 24px card soup.
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "10px",
      },
      boxShadow: {
        // Flat-first: elevation only where something floats (menus, dialogs).
        overlay: "0 8px 24px rgba(28, 25, 23, 0.14)",
      },
    },
  },
};

export default config;
