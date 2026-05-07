import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ─── UrjaYukti AI Design Tokens ────────────────────────────────────────
        bg: "#0B0D14",
        panel: "#0F1420",
        cardBg: "#141B2D",
        card2: "#1A2340",
        glass: "rgba(255,255,255,0.04)",
        border: "rgba(255,255,255,0.07)",
        borderHi: "rgba(2,195,154,0.5)",
        primary: "#02C39A",
        teal: "#0891B2",
        blue: "#3B82F6",
        cyan: "#00E5FF",
        text: "#F0F6FC",
        sub: "#8B949E",
        dim: "#30363D",
        warn: "#F59E0B",
        danger: "#F43F5E",
        purple: "#A78BFA",
        success: "#10B981",

        // ─── Shadcn/ui Variables (preserved) ────────────────────────────────────
        shadcn: {
          background: "hsl(var(--background))",
          foreground: "hsl(var(--foreground))",
          card: "hsl(var(--card))",
          "card-foreground": "hsl(var(--card-foreground))",
          popover: "hsl(var(--popover))",
          "popover-foreground": "hsl(var(--popover-foreground))",
          primary: "hsl(var(--primary))",
          "primary-foreground": "hsl(var(--primary-foreground))",
          secondary: "hsl(var(--secondary))",
          "secondary-foreground": "hsl(var(--secondary-foreground))",
          muted: "hsl(var(--muted))",
          "muted-foreground": "hsl(var(--muted-foreground))",
          accent: "hsl(var(--accent))",
          "accent-foreground": "hsl(var(--accent-foreground))",
          destructive: "hsl(var(--destructive))",
          "destructive-foreground": "hsl(var(--destructive-foreground))",
          input: "hsl(var(--input))",
          ring: "hsl(var(--ring))",
        },
      },
      fontFamily: {
        sans: ['var(--font-dm)', 'system-ui', 'sans-serif'],
        display: ['var(--font-syne)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {

        // ─── Dashboard Keyframes ───────────────────────────────────────────────
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        pulse: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.4" },
        },
        spin: {
          to: { transform: "rotate(360deg)" },
        },
        glow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(2,195,154,0)" },
          "50%": { boxShadow: "0 0 0 6px rgba(2,195,154,0.12)" },
        },
        ticker: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-600px 0" },
          "100%": { backgroundPosition: "600px 0" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.96)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        slideRight: {
          "0%": { width: "0" },
          "100%": { width: "100%" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },

        // ─── Logo Keyframes ─────────────────────────────────────────────────────
        logoGlow: {
          "0%, 100%": { filter: "drop-shadow(0 0 6px rgba(2,195,154,0.5))" },
          "50%": { filter: "drop-shadow(0 0 20px rgba(2,195,154,0.95))" },
        },
        logoPulse: {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.1)" },
        },
        logoDash: {
          to: { strokeDashoffset: "-22" },
        },

        // ─── ZoneMap Keyframes ───────────────────────────────────────────────────
        drawPerim: {
          "0%": { strokeDashoffset: "3200" },
          "100%": { strokeDashoffset: "0" },
        },
        perimGlow: {
          "0%, 100%": {
            filter: "drop-shadow(0 0 5px #00E5FF) drop-shadow(0 0 12px rgba(0,229,255,0.5))",
          },
          "50%": {
            filter: "drop-shadow(0 0 12px #00E5FF) drop-shadow(0 0 28px rgba(0,229,255,0.8))",
          },
        },
        rippleOut: {
          "0%": { transform: "scale(1)", opacity: "0.55" },
          "100%": { transform: "scale(3.2)", opacity: "0" },
        },
        innerBeat: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.95" },
          "50%": { transform: "scale(1.35)", opacity: "1" },
        },
        flowMove: {
          to: { strokeDashoffset: "-22" },
        },
        slideInR: {
          "0%": { opacity: "0", transform: "translateX(20px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        liveBlink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
      animation: {
        // ─── Dashboard Animations ───────────────────────────────────────────────
        "fade-up": "fadeUp 0.45s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "fade-in": "fadeIn 0.3s ease forwards",
        "pulse": "pulse 2s ease-in-out infinite",
        "spin": "spin 1s linear infinite",
        "glow": "glow 2s ease-in-out infinite",
        "ticker": "ticker 24s linear infinite",
        "blink": "blink 1s step-end infinite",
        "shimmer": "shimmer 1.6s ease-in-out infinite",
        "scale-in": "scaleIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "slide-right": "slideRight 0.4s ease forwards",
        "float": "float 4s ease-in-out infinite",

        // ─── Logo Animations ───────────────────────────────────────────────────
        "logo-glow": "logoGlow 3s ease-in-out infinite",
        "logo-pulse": "logoPulse 2.5s ease-in-out infinite",
        "logo-dash": "logoDash 1.4s linear infinite",

        // ─── ZoneMap Animations ────────────────────────────────────────────────
        "draw-perim": "drawPerim 1.4s cubic-bezier(0.4, 0, 0.2, 1) forwards, perimGlow 2.8s ease-in-out 1.4s infinite",
        "ripple": "rippleOut 2s ease-out infinite",
        "dot-beat": "innerBeat 1.6s ease-in-out infinite",
        "flow-dash": "flowMove 1.2s linear infinite",
        "slide-inR": "slideInR 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "live-blink": "liveBlink 2s ease-in-out infinite",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
}

export default config
