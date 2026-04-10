# Landing Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current 718-line static landing page with a premium, animated, dual-theme landing page built with Framer Motion + Tailwind CSS.

**Architecture:** The landing page is decomposed into 13 independent client components under `web/components/landing/`, each responsible for one section. A root `LandingPage` component assembles them all. The theme system uses CSS custom properties defined in the existing `web/styles/globals.css` and toggled via [`next-themes`](https://github.com/pacocoursey/next-themes), which is already wired into `web/app/layout.tsx` with `attribute="data-theme"`, `storageKey="rf-theme"`, and `defaultTheme="system"`. Landing components consume `useTheme` from `next-themes` directly — no custom `ThemeProvider` is created.

**Tech Stack:** Next.js 16, React 18, Framer Motion (LazyMotion + domAnimation), Tailwind CSS v4 (via `@tailwindcss/postcss`), Inter + JetBrains Mono fonts via `next/font/google`.

---

## File Map

### New files (create)

| File | Purpose |
|------|---------|
| `web/postcss.config.mjs` | PostCSS config with `@tailwindcss/postcss` plugin |
| `web/components/landing/navbar.tsx` | Sticky nav with glass blur |
| `web/components/landing/hero.tsx` | Centered hero with stagger animation |
| `web/components/landing/social-proof.tsx` | Animated counter stats bar |
| `web/components/landing/how-it-works.tsx` | 3-step process cards |
| `web/components/landing/feature-showcase.tsx` | 3 alternating feature sections |
| `web/components/landing/product-preview.tsx` | Full-width product screenshot with parallax |
| `web/components/landing/testimonials.tsx` | Customer testimonial cards |
| `web/components/landing/pricing.tsx` | 3-tier pricing with monthly/annual toggle |
| `web/components/landing/faq.tsx` | Accordion FAQ |
| `web/components/landing/final-cta.tsx` | Bottom coral gradient CTA |
| `web/components/landing/footer.tsx` | Footer with links |
| `web/components/landing/index.tsx` | Main `LandingPage` assembler component |

### Modified files

| File | Change |
|------|--------|
| `web/styles/globals.css` | Append landing theme CSS custom properties (`--landing-*`) to the existing `:root` and `[data-theme="dark"]` blocks |
| `web/app/layout.tsx` | No changes required — already wraps the tree with `next-themes` `ThemeProvider`, `AuthProvider`, `TooltipProvider`, and `<Toaster richColors position="bottom-right" />` |
| `web/app/page.tsx` | Replace with thin wrapper importing `LandingPage` |
| `web/package.json` | Add `framer-motion`, `tailwindcss`, `@tailwindcss/postcss` |

---

### Task 1: Install Dependencies and Configure Tailwind

**Files:**
- Create: `web/postcss.config.mjs`
- Modify: `web/package.json`

- [ ] **Step 1: Install dependencies**

Run:
```bash
cd web && npm install framer-motion tailwindcss @tailwindcss/postcss
```

- [ ] **Step 2: Create PostCSS config**

Create `web/postcss.config.mjs`:
```js
/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

- [ ] **Step 3: Verify installation**

Run:
```bash
cd web && npm run build
```
Expected: Build passes (Tailwind not yet imported anywhere, so no change in output)

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json web/postcss.config.mjs
git commit -m "feat(landing): install framer-motion, tailwindcss, and postcss plugin"
```

---

### Task 2: Theme CSS Custom Properties

**Files:**
- Modify: `web/styles/globals.css`

- [ ] **Step 1: Append theme tokens to globals.css**

The existing `web/styles/globals.css` already imports Tailwind, defines `:root` and `[data-theme="dark"]` blocks, and is the single stylesheet imported by `web/app/layout.tsx`. Do NOT create a new `landing.css` — append the landing-specific custom properties below into the existing `:root` and `[data-theme="dark"]` selectors in `globals.css`, and add the landing-page helper rules at the bottom of the file.

```css
/* ==========================================================================
   THEME SYSTEM - LANDING PAGE CSS CUSTOM PROPERTIES
   ========================================================================== */

:root {
  --landing-bg: #fafafa;
  --landing-surface: #ffffff;
  --landing-card: #f4f4f5;
  --landing-border: #e4e4e7;
  --landing-text: #09090b;
  --landing-text-muted: #71717a;
  --landing-accent: #FF6B6B;
  --landing-accent-hover: #FF4757;
  --landing-accent-glow: rgba(255, 107, 107, 0.15);
  --landing-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  --landing-shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.08);
}

[data-theme="dark"] {
  --landing-bg: #0a0a0b;
  --landing-surface: #141416;
  --landing-card: #1a1a1f;
  --landing-border: #2a2a30;
  --landing-text: #fafafa;
  --landing-text-muted: #a1a1aa;
  --landing-accent: #FF6B6B;
  --landing-accent-hover: #FF4757;
  --landing-accent-glow: rgba(255, 107, 107, 0.2);
  --landing-shadow: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);
  --landing-shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.4);
}

/* ==========================================================================
   LANDING PAGE - BASE STYLES
   ========================================================================== */

.landing-page {
  background-color: var(--landing-bg);
  color: var(--landing-text);
  font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

.landing-page h1,
.landing-page h2,
.landing-page h3 {
  color: var(--landing-text);
  margin: 0;
}

.landing-page p {
  color: var(--landing-text-muted);
}

/* Smooth scroll for anchor links */
html {
  scroll-behavior: smooth;
}

/* Accent gradient for decorative elements */
.accent-gradient {
  background: linear-gradient(135deg, var(--landing-accent) 0%, var(--landing-accent-hover) 100%);
}

/* Glass blur effect for navbar */
.glass-blur {
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
```

- [ ] **Step 2: Verify the layout needs no changes**

No edit to `web/app/layout.tsx` is required. The layout already imports `../styles/globals.css` and wraps the tree with:

- `next-themes` `ThemeProvider` (`attribute="data-theme"`, `defaultTheme="system"`, `enableSystem`, `disableTransitionOnChange`, `storageKey="rf-theme"`)
- `AuthProvider` (from `../components/auth/auth-provider`)
- `TooltipProvider` (from `@/components/ui/tooltip`)
- `<Toaster richColors position="bottom-right" />` (from `@/components/ui/sonner`)

Theme tokens appended to `globals.css` in Step 1 take effect automatically because `[data-theme="dark"]` on `<html>` is already driven by `next-themes`.

- [ ] **Step 3: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes with no errors

- [ ] **Step 4: Commit**

```bash
git add web/styles/globals.css
git commit -m "feat(landing): add theme CSS custom properties"
```

---

### Task 3: Theme hook — already wired via `next-themes` (no action required)

**Status:** No files to create or modify. The app already uses `ThemeProvider` from `next-themes` in `web/app/layout.tsx`. Do NOT create `web/components/landing/theme-provider.tsx`.

Current `web/app/layout.tsx` (verbatim — do not modify):

```tsx
import type { Metadata } from "next";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";

import "../styles/globals.css";
import { AuthProvider } from "../components/auth/auth-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "RedditFlow",
  description:
    "AI visibility, community engagement, and content workflows for brands building authority across modern discovery channels.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={cn(inter.variable)}>
      <body>
        <ThemeProvider
          attribute="data-theme"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
          storageKey="rf-theme"
        >
          <AuthProvider>
            <TooltipProvider>
              {children}
              <Toaster richColors position="bottom-right" />
            </TooltipProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
```

**Key points for landing components:**

- Import `useTheme` from `next-themes`, **not** from a local `./theme-provider`:
  ```tsx
  import { useTheme } from "next-themes";
  const { theme, setTheme, resolvedTheme } = useTheme();
  ```
- The toggle handler is `setTheme(theme === "dark" ? "light" : "dark")` — `next-themes`' hook returns `{ theme, setTheme, resolvedTheme, ... }`, not a custom `{ theme, toggleTheme }` shape.
- The theme attribute is `data-theme` on `<html>`, so CSS selectors use `[data-theme="dark"]` (matching the existing `globals.css`), not `.dark`.
- `storageKey` is `"rf-theme"`.
- To avoid SSR hydration mismatch, guard theme-dependent rendering behind a `useEffect` mount flag and read `resolvedTheme` after mount (standard `next-themes` pattern).
- `TooltipProvider` and `<Toaster richColors position="bottom-right" />` are already mounted globally — landing components can use `Tooltip` and `toast()` from `sonner` directly without rewrapping.

---

### Task 4: Navbar Component

**Files:**
- Create: `web/components/landing/navbar.tsx`

- [ ] **Step 1: Create the navbar component**

Create `web/components/landing/navbar.tsx`:
```tsx
"use client";

import Link from "next/link";
import { motion, useScroll } from "framer-motion";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

const navLinks = [
  { label: "Features", href: "#features" },
  { label: "Pricing", href: "#pricing" },
  { label: "Testimonials", href: "#testimonials" },
];

export function Navbar() {
  // Guard against SSR hydration mismatch: only read resolvedTheme after mount.
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const theme = mounted ? resolvedTheme : undefined;
  const toggleTheme = () => setTheme(theme === "dark" ? "light" : "dark");
  const { scrollY } = useScroll();

  const isScrolled = scrollY > 100;

  return (
    <motion.nav
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        backgroundColor: isScrolled
          ? theme === "dark"
            ? "rgba(10, 10, 11, 0.8)"
            : "rgba(250, 250, 250, 0.8)"
          : "transparent",
        backdropFilter: isScrolled ? "blur(12px)" : "none",
        WebkitBackdropFilter: isScrolled ? "blur(12px)" : "none",
        borderBottom: isScrolled
          ? `1px solid ${theme === "dark" ? "#2a2a30" : "#e4e4e7"}`
          : "1px solid transparent",
      }}
    >
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="text-lg font-bold tracking-tight" style={{ color: "var(--landing-text)" }}>
            RedditFlow
          </Link>

          {/* Nav Links */}
          <div className="hidden items-center gap-8 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="relative text-sm font-medium transition-colors duration-200 hover:text-[var(--landing-accent)]"
                style={{ color: "var(--landing-text-muted)" }}
              >
                {link.label}
              </a>
            ))}
          </div>

          {/* Right side: theme toggle + CTA */}
          <div className="flex items-center gap-4">
            <button
              onClick={toggleTheme}
              className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors duration-200"
              style={{
                backgroundColor: "var(--landing-card)",
                color: "var(--landing-text-muted)",
              }}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
            <Link
              href="/register"
              className="rounded-lg px-4 py-2 text-sm font-semibold text-white transition-all duration-200"
              style={{ backgroundColor: "var(--landing-accent)" }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--landing-accent-hover)")}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "var(--landing-accent)")}
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </div>
    </motion.nav>
  );
}
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web/components/landing/navbar.tsx
git commit -m "feat(landing): add sticky navbar with glass blur and theme toggle"
```

---

### Task 5: Hero Section

**Files:**
- Create: `web/components/landing/hero.tsx`

- [ ] **Step 1: Create the hero component**

Create `web/components/landing/hero.tsx`:
```tsx
"use client";

import Link from "next/link";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

const containerVariants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.12 },
  },
};

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } },
};

export function Hero() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const imageY = useTransform(scrollYProgress, [0, 1], [0, 30]);

  return (
    <section ref={ref} className="relative overflow-hidden pb-8 pt-32 md:pb-16 md:pt-44">
      {/* Decorative gradient orbs */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full opacity-20 blur-3xl"
        style={{ background: "radial-gradient(circle, var(--landing-accent) 0%, transparent 70%)" }}
      />

      <motion.div
        className="relative mx-auto max-w-7xl px-6 text-center"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Eyebrow */}
        <motion.div variants={fadeUp}>
          <span
            className="mb-6 inline-block rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-widest"
            style={{
              backgroundColor: "var(--landing-accent-glow)",
              color: "var(--landing-accent)",
            }}
          >
            AI Visibility Platform
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          variants={fadeUp}
          className="mx-auto max-w-4xl text-4xl font-bold leading-tight tracking-tight md:text-6xl lg:text-7xl"
          style={{ color: "var(--landing-text)" }}
        >
          See How AI Talks About{" "}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: "linear-gradient(135deg, var(--landing-accent), var(--landing-accent-hover))",
            }}
          >
            Your Brand
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          variants={fadeUp}
          className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed md:text-xl"
          style={{ color: "var(--landing-text-muted)" }}
        >
          RedditFlow tracks your brand across ChatGPT, Perplexity, Gemini, and Claude — then finds
          the Reddit conversations that shape what they say.
        </motion.p>

        {/* CTA Buttons */}
        <motion.div variants={fadeUp} className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/register"
            className="inline-flex h-12 items-center justify-center rounded-xl px-8 text-base font-semibold text-white transition-all duration-200"
            style={{ backgroundColor: "var(--landing-accent)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "var(--landing-accent-hover)";
              e.currentTarget.style.transform = "scale(1.02)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "var(--landing-accent)";
              e.currentTarget.style.transform = "scale(1)";
            }}
          >
            Start Free Trial
          </Link>
          <a
            href="#features"
            className="inline-flex h-12 items-center justify-center rounded-xl border px-8 text-base font-semibold transition-all duration-200"
            style={{
              borderColor: "var(--landing-border)",
              color: "var(--landing-text)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--landing-accent)";
              e.currentTarget.style.color = "var(--landing-accent)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--landing-border)";
              e.currentTarget.style.color = "var(--landing-text)";
            }}
          >
            Watch Demo
          </a>
        </motion.div>

        {/* Product Screenshot Mockup */}
        <motion.div
          variants={fadeUp}
          style={{ y: imageY }}
          className="relative mx-auto mt-16 max-w-5xl"
        >
          <div
            className="overflow-hidden rounded-2xl border p-1"
            style={{
              borderColor: "var(--landing-border)",
              boxShadow: "var(--landing-shadow-lg), 0 0 80px var(--landing-accent-glow)",
            }}
          >
            <div
              className="rounded-xl p-6"
              style={{ backgroundColor: "var(--landing-surface)" }}
            >
              {/* Mock dashboard UI */}
              <div className="flex items-center gap-2 pb-4">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
                <div
                  className="ml-4 h-6 flex-1 rounded-md"
                  style={{ backgroundColor: "var(--landing-card)" }}
                />
              </div>
              <div className="grid grid-cols-4 gap-4">
                {/* Visibility Score */}
                <div
                  className="col-span-1 rounded-lg p-4"
                  style={{ backgroundColor: "var(--landing-card)" }}
                >
                  <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>
                    Visibility Score
                  </div>
                  <div className="mt-2 text-3xl font-bold" style={{ color: "var(--landing-accent)" }}>
                    87
                  </div>
                  <div className="mt-1 text-xs" style={{ color: "var(--landing-text-muted)" }}>
                    +12% this week
                  </div>
                </div>
                {/* AI Model Cards */}
                {["ChatGPT", "Perplexity", "Gemini"].map((model) => (
                  <div
                    key={model}
                    className="rounded-lg p-4"
                    style={{ backgroundColor: "var(--landing-card)" }}
                  >
                    <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>
                      {model}
                    </div>
                    <div className="mt-2 text-lg font-bold" style={{ color: "var(--landing-text)" }}>
                      {model === "ChatGPT" ? "Mentioned" : model === "Perplexity" ? "Cited" : "Detected"}
                    </div>
                    <div className="mt-2 h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: "var(--landing-border)" }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: model === "ChatGPT" ? "92%" : model === "Perplexity" ? "78%" : "65%",
                          backgroundColor: "var(--landing-accent)",
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              {/* Opportunity list mockup */}
              <div className="mt-4 grid grid-cols-2 gap-3">
                {["r/SaaS — Best CRM for startups?", "r/Marketing — AI tools comparison 2025"].map((title) => (
                  <div
                    key={title}
                    className="rounded-lg border p-3"
                    style={{
                      borderColor: "var(--landing-border)",
                      backgroundColor: "var(--landing-card)",
                    }}
                  >
                    <div className="text-sm font-medium" style={{ color: "var(--landing-text)" }}>
                      {title}
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: "var(--landing-accent-glow)",
                          color: "var(--landing-accent)",
                        }}
                      >
                        High Intent
                      </span>
                      <span className="text-xs" style={{ color: "var(--landing-text-muted)" }}>
                        Score: 94
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web/components/landing/hero.tsx
git commit -m "feat(landing): add hero section with stagger animations and dashboard mockup"
```

---

### Task 6: Social Proof Bar

**Files:**
- Create: `web/components/landing/social-proof.tsx`

- [ ] **Step 1: Create the social proof component**

Create `web/components/landing/social-proof.tsx`:
```tsx
"use client";

import { motion, useInView } from "framer-motion";
import { useRef, useEffect, useState } from "react";

interface StatProps {
  value: number;
  suffix: string;
  label: string;
}

function AnimatedStat({ value, suffix, label }: StatProps) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!isInView) return;
    let start = 0;
    const duration = 2000;
    const startTime = performance.now();

    function animate(currentTime: number) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      start = Math.round(eased * value);
      setCount(start);
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    }

    requestAnimationFrame(animate);
  }, [isInView, value]);

  return (
    <div ref={ref} className="text-center">
      <div
        className="text-3xl font-bold tracking-tight md:text-4xl"
        style={{ color: "var(--landing-text)" }}
      >
        {count.toLocaleString()}
        {suffix}
      </div>
      <div className="mt-1 text-sm" style={{ color: "var(--landing-text-muted)" }}>
        {label}
      </div>
    </div>
  );
}

const stats: StatProps[] = [
  { value: 500, suffix: "+", label: "Brands Tracked" },
  { value: 1000000, suffix: "+", label: "Posts Analyzed" },
  { value: 4, suffix: "", label: "AI Models Monitored" },
  { value: 98, suffix: "%", label: "Uptime" },
];

export function SocialProof() {
  return (
    <section className="py-16 md:py-20">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-2 gap-8 rounded-2xl border p-8 md:grid-cols-4 md:gap-12"
          style={{
            borderColor: "var(--landing-border)",
            backgroundColor: "var(--landing-surface)",
          }}
        >
          {stats.map((stat) => (
            <AnimatedStat key={stat.label} {...stat} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web/components/landing/social-proof.tsx
git commit -m "feat(landing): add social proof bar with animated counters"
```

---

### Task 7: How It Works Section

**Files:**
- Create: `web/components/landing/how-it-works.tsx`

- [ ] **Step 1: Create the how-it-works component**

Create `web/components/landing/how-it-works.tsx`:
```tsx
"use client";

import { motion } from "framer-motion";

const steps = [
  {
    number: "01",
    title: "Connect Your Brand",
    description:
      "Enter your website. Our AI builds a complete profile of your business, audience, and voice.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  {
    number: "02",
    title: "Track AI Visibility",
    description:
      "See how ChatGPT, Perplexity, Gemini, and Claude mention your brand. Spot gaps where competitors appear instead.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    number: "03",
    title: "Engage Authentically",
    description:
      "Discover high-intent Reddit conversations and draft helpful, brand-aware replies — never spammy.",
    icon: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.15 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export function HowItWorks() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            How It Works
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Three steps to AI visibility
          </h2>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="mt-14 grid gap-6 md:grid-cols-3"
        >
          {steps.map((step) => (
            <motion.div
              key={step.number}
              variants={cardVariants}
              whileHover={{ y: -4 }}
              transition={{ duration: 0.2 }}
              className="group rounded-2xl border p-8 transition-shadow duration-300"
              style={{
                borderColor: "var(--landing-border)",
                backgroundColor: "var(--landing-surface)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--landing-accent)";
                e.currentTarget.style.boxShadow = "0 10px 40px var(--landing-accent-glow)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--landing-border)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div
                className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl"
                style={{ backgroundColor: "var(--landing-accent-glow)", color: "var(--landing-accent)" }}
              >
                {step.icon}
              </div>
              <div
                className="mb-2 text-xs font-bold tracking-wider"
                style={{ color: "var(--landing-accent)" }}
              >
                STEP {step.number}
              </div>
              <h3
                className="mb-3 text-xl font-semibold tracking-tight"
                style={{ color: "var(--landing-text)" }}
              >
                {step.title}
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--landing-text-muted)" }}
              >
                {step.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web/components/landing/how-it-works.tsx
git commit -m "feat(landing): add how-it-works section with staggered card animations"
```

---

### Task 8: Feature Showcase (3 Alternating Sections)

**Files:**
- Create: `web/components/landing/feature-showcase.tsx`

- [ ] **Step 1: Create the feature showcase component**

Create `web/components/landing/feature-showcase.tsx`:
```tsx
"use client";

import { motion } from "framer-motion";

const features = [
  {
    title: "AI Visibility Dashboard",
    description:
      "Track brand mentions across every major AI model with sentiment analysis and citation tracking. See where you appear, where competitors rank, and what changes week over week.",
    mockup: (
      <div className="grid gap-3">
        {/* Visibility score + model comparison */}
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg p-4" style={{ backgroundColor: "var(--landing-card)" }}>
            <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>Overall Visibility</div>
            <div className="mt-1 text-4xl font-bold" style={{ color: "var(--landing-accent)" }}>87<span className="text-lg">/100</span></div>
            <div className="mt-2 text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>+12pts this month</div>
          </div>
          <div className="grid gap-2">
            {[
              { name: "ChatGPT", pct: 92 },
              { name: "Perplexity", pct: 78 },
              { name: "Gemini", pct: 65 },
              { name: "Claude", pct: 71 },
            ].map((m) => (
              <div key={m.name} className="flex items-center gap-2 rounded-lg p-2" style={{ backgroundColor: "var(--landing-card)" }}>
                <span className="w-16 text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>{m.name}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: "var(--landing-border)" }}>
                  <div className="h-full rounded-full" style={{ width: `${m.pct}%`, backgroundColor: "var(--landing-accent)" }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        {/* Citation list */}
        <div className="rounded-lg p-4" style={{ backgroundColor: "var(--landing-card)" }}>
          <div className="mb-2 text-xs font-semibold" style={{ color: "var(--landing-text)" }}>Recent Citations</div>
          {["Mentioned in top 3 for 'best CRM software'", "Cited as alternative to HubSpot in ChatGPT", "New source gap detected on Perplexity"].map((c, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5">
              <div className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: i < 2 ? "var(--landing-accent)" : "var(--landing-text-muted)" }} />
              <span className="text-xs" style={{ color: "var(--landing-text-muted)" }}>{c}</span>
            </div>
          ))}
        </div>
      </div>
    ),
    reverse: false,
  },
  {
    title: "Smart Opportunity Discovery",
    description:
      "AI-powered scoring finds the Reddit conversations where your expertise matters most. Every opportunity is scored for relevance, intent, recency, and subreddit rule compliance.",
    mockup: (
      <div className="grid gap-3">
        {[
          { subreddit: "r/SaaS", title: "Best CRM for early-stage startups?", score: 94, intent: "Recommendation", comments: "3" },
          { subreddit: "r/Marketing", title: "Switching from HubSpot — what's better?", score: 89, intent: "Comparison", comments: "7" },
          { subreddit: "r/Entrepreneur", title: "Tools that actually save time for small teams", score: 82, intent: "Discussion", comments: "12" },
        ].map((opp) => (
          <div key={opp.title} className="flex items-start gap-3 rounded-lg border p-3" style={{ borderColor: "var(--landing-border)", backgroundColor: "var(--landing-card)" }}>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold" style={{ backgroundColor: "var(--landing-accent-glow)", color: "var(--landing-accent)" }}>
              {opp.score}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>{opp.subreddit}</div>
              <div className="text-sm font-semibold" style={{ color: "var(--landing-text)" }}>{opp.title}</div>
              <div className="mt-1 flex gap-2">
                <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: "var(--landing-accent-glow)", color: "var(--landing-accent)" }}>{opp.intent}</span>
                <span className="text-xs" style={{ color: "var(--landing-text-muted)" }}>{opp.comments} comments</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    ),
    reverse: true,
  },
  {
    title: "Brand-Aware Content Studio",
    description:
      "Generate authentic replies and posts that match your voice, checked against subreddit rules. Never sound spammy — every draft is helpful, relevant, and human.",
    mockup: (
      <div className="grid gap-3">
        <div className="rounded-lg p-4" style={{ backgroundColor: "var(--landing-card)" }}>
          <div className="mb-2 text-xs font-semibold" style={{ color: "var(--landing-text)" }}>Generated Reply</div>
          <div className="space-y-2 text-sm leading-relaxed" style={{ color: "var(--landing-text-muted)" }}>
            <p>Great question! I switched to a CRM built specifically for early-stage startups and it made a huge difference. The key things I looked for were...</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "var(--landing-card)" }}>
            <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>Brand Voice</div>
            <div className="mt-1 text-sm font-bold" style={{ color: "var(--landing-accent)" }}>98% Match</div>
          </div>
          <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "var(--landing-card)" }}>
            <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>Rule Check</div>
            <div className="mt-1 text-sm font-bold" style={{ color: "var(--landing-accent)" }}>Compliant</div>
          </div>
          <div className="rounded-lg p-3 text-center" style={{ backgroundColor: "var(--landing-card)" }}>
            <div className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>Spam Score</div>
            <div className="mt-1 text-sm font-bold" style={{ color: "var(--landing-accent)" }}>0%</div>
          </div>
        </div>
      </div>
    ),
    reverse: false,
  },
];

export function FeatureShowcase() {
  return (
    <section id="features" className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            Features
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Everything you need to own your narrative
          </h2>
        </motion.div>

        <div className="mt-16 space-y-24">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.6 }}
              className={`grid items-center gap-12 md:grid-cols-2 ${feature.reverse ? "md:direction-rtl" : ""}`}
              style={{ direction: feature.reverse ? "rtl" : "ltr" }}
            >
              {/* Text side */}
              <div style={{ direction: "ltr" }}>
                <h3
                  className="mb-4 text-2xl font-bold tracking-tight md:text-3xl"
                  style={{ color: "var(--landing-text)" }}
                >
                  {feature.title}
                </h3>
                <p
                  className="text-base leading-relaxed"
                  style={{ color: "var(--landing-text-muted)" }}
                >
                  {feature.description}
                </p>
              </div>

              {/* Mockup side */}
              <div
                className="rounded-2xl border p-6"
                style={{
                  borderColor: "var(--landing-border)",
                  backgroundColor: "var(--landing-surface)",
                  direction: "ltr",
                }}
              >
                {feature.mockup}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes

- [ ] **Step 3: Commit**

```bash
git add web/components/landing/feature-showcase.tsx
git commit -m "feat(landing): add feature showcase with alternating layouts"
```

---

### Task 9: Product Preview, Testimonials, Pricing, FAQ, Final CTA, Footer

**Files:**
- Create: `web/components/landing/product-preview.tsx`
- Create: `web/components/landing/testimonials.tsx`
- Create: `web/components/landing/pricing.tsx`
- Create: `web/components/landing/faq.tsx`
- Create: `web/components/landing/final-cta.tsx`
- Create: `web/components/landing/footer.tsx`

- [ ] **Step 1: Create product-preview.tsx**

Create `web/components/landing/product-preview.tsx`:
```tsx
"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

export function ProductPreview() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [20, -20]);

  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            Product
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Your AI command center
          </h2>
          <p
            className="mx-auto mt-4 max-w-2xl text-base"
            style={{ color: "var(--landing-text-muted)" }}
          >
            One dashboard to track AI visibility, discover opportunities, and generate content — all in real time.
          </p>
        </motion.div>

        <motion.div
          ref={ref}
          style={{ y }}
          className="mx-auto mt-12 max-w-5xl"
        >
          <div
            className="overflow-hidden rounded-2xl border"
            style={{
              borderColor: "var(--landing-border)",
              boxShadow: "var(--landing-shadow-lg)",
            }}
          >
            <div className="p-1">
              <div className="rounded-xl p-6" style={{ backgroundColor: "var(--landing-surface)" }}>
                {/* Full dashboard mockup */}
                <div className="grid grid-cols-3 gap-4">
                  {/* Left sidebar */}
                  <div className="col-span-1 space-y-3">
                    <div className="rounded-lg p-3" style={{ backgroundColor: "var(--landing-card)" }}>
                      <div className="text-xs font-semibold" style={{ color: "var(--landing-text)" }}>Workspace</div>
                      <div className="mt-2 space-y-1.5">
                        {["Dashboard", "Visibility", "Discovery", "Content", "Analytics"].map((item, i) => (
                          <div key={item} className="rounded px-2 py-1 text-xs" style={{
                            backgroundColor: i === 0 ? "var(--landing-accent-glow)" : "transparent",
                            color: i === 0 ? "var(--landing-accent)" : "var(--landing-text-muted)",
                            fontWeight: i === 0 ? 600 : 400,
                          }}>
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg p-3" style={{ backgroundColor: "var(--landing-card)" }}>
                      <div className="text-xs font-semibold" style={{ color: "var(--landing-text)" }}>Active Project</div>
                      <div className="mt-1 text-xs" style={{ color: "var(--landing-text-muted)" }}>Acme Corp</div>
                      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full" style={{ backgroundColor: "var(--landing-border)" }}>
                        <div className="h-full rounded-full" style={{ width: "78%", backgroundColor: "var(--landing-accent)" }} />
                      </div>
                      <div className="mt-1 text-xs" style={{ color: "var(--landing-text-muted)" }}>78% profile complete</div>
                    </div>
                  </div>
                  {/* Main content */}
                  <div className="col-span-2 space-y-3">
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: "Visibility Score", value: "87", change: "+12%" },
                        { label: "Opportunities", value: "142", change: "+28" },
                        { label: "Drafts Ready", value: "38", change: "+9" },
                      ].map((kpi) => (
                        <div key={kpi.label} className="rounded-lg p-3" style={{ backgroundColor: "var(--landing-card)" }}>
                          <div className="text-xs" style={{ color: "var(--landing-text-muted)" }}>{kpi.label}</div>
                          <div className="mt-1 text-xl font-bold" style={{ color: "var(--landing-text)" }}>{kpi.value}</div>
                          <div className="mt-0.5 text-xs font-medium" style={{ color: "var(--landing-accent)" }}>{kpi.change}</div>
                        </div>
                      ))}
                    </div>
                    {/* Opportunity table */}
                    <div className="rounded-lg p-3" style={{ backgroundColor: "var(--landing-card)" }}>
                      <div className="mb-2 text-xs font-semibold" style={{ color: "var(--landing-text)" }}>Top Opportunities</div>
                      <div className="space-y-1.5">
                        {[
                          { sub: "r/SaaS", post: "Best CRM for startups 2025?", score: 94 },
                          { sub: "r/Marketing", post: "HubSpot alternatives that don't break the bank", score: 89 },
                          { sub: "r/SmallBusiness", post: "What CRM do you use and why?", score: 85 },
                        ].map((opp) => (
                          <div key={opp.post} className="flex items-center justify-between rounded px-2 py-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium" style={{ color: "var(--landing-text-muted)" }}>{opp.sub}</span>
                              <span className="text-xs" style={{ color: "var(--landing-text)" }}>{opp.post}</span>
                            </div>
                            <span className="rounded-full px-2 py-0.5 text-xs font-bold" style={{ backgroundColor: "var(--landing-accent-glow)", color: "var(--landing-accent)" }}>{opp.score}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Create testimonials.tsx**

Create `web/components/landing/testimonials.tsx`:
```tsx
"use client";

import { motion } from "framer-motion";

const testimonials = [
  {
    quote: "RedditFlow showed us that ChatGPT was recommending our competitor in 8 out of 10 queries. Within a month of targeted engagement, we flipped that to 7 out of 10 mentioning us.",
    name: "Sarah Chen",
    role: "Head of Growth",
    company: "TechStack",
  },
  {
    quote: "The opportunity scoring is incredible. It surfaces exactly the conversations where our expertise adds value — and the AI drafts are surprisingly natural. Saves us 10+ hours a week.",
    name: "Marcus Rivera",
    role: "SEO Lead",
    company: "Growth Agency Co.",
  },
  {
    quote: "We went from invisible in AI search results to being the #1 recommended tool in our category on Perplexity. RedditFlow made it systematic instead of random.",
    name: "Aisha Patel",
    role: "Founder",
    company: "ClearView Analytics",
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.15 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export function Testimonials() {
  return (
    <section id="testimonials" className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            Testimonials
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Trusted by growth teams everywhere
          </h2>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="mt-14 grid gap-6 md:grid-cols-3"
        >
          {testimonials.map((t) => (
            <motion.div
              key={t.name}
              variants={cardVariants}
              whileHover={{ y: -4 }}
              className="flex flex-col rounded-2xl border p-6"
              style={{
                borderColor: "var(--landing-border)",
                backgroundColor: "var(--landing-surface)",
              }}
            >
              {/* Stars */}
              <div className="mb-4 flex gap-1" style={{ color: "var(--landing-accent)" }}>
                {Array.from({ length: 5 }).map((_, i) => (
                  <svg key={i} width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                  </svg>
                ))}
              </div>
              <p className="flex-1 text-sm leading-relaxed" style={{ color: "var(--landing-text-muted)" }}>
                &ldquo;{t.quote}&rdquo;
              </p>
              <div className="mt-6 flex items-center gap-3">
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white"
                  style={{ backgroundColor: "var(--landing-accent)" }}
                >
                  {t.name.charAt(0)}
                </div>
                <div>
                  <div className="text-sm font-semibold" style={{ color: "var(--landing-text)" }}>{t.name}</div>
                  <div className="text-xs" style={{ color: "var(--landing-text-muted)" }}>{t.role}, {t.company}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Create pricing.tsx**

Create `web/components/landing/pricing.tsx`:
```tsx
"use client";

import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const tiers = [
  {
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Get started with basic AI visibility tracking.",
    features: [
      "1 project",
      "50 scans per month",
      "Basic visibility tracking",
      "Community support",
    ],
    cta: "Get Started",
    ctaLink: "/register",
    highlighted: false,
  },
  {
    name: "Pro",
    monthlyPrice: 49,
    annualPrice: 39,
    description: "Full visibility suite with content studio.",
    features: [
      "5 projects",
      "500 scans per month",
      "Full visibility suite",
      "Content studio",
      "Smart opportunity discovery",
      "Priority support",
    ],
    cta: "Start Free Trial",
    ctaLink: "/register",
    highlighted: true,
  },
  {
    name: "Enterprise",
    monthlyPrice: null,
    annualPrice: null,
    description: "Custom solutions for scaling teams.",
    features: [
      "Unlimited projects",
      "Unlimited scans",
      "Custom integrations",
      "Dedicated support",
      "SLA guarantee",
      "Advanced analytics",
    ],
    cta: "Schedule Demo",
    ctaLink: "mailto:hello@redditflow.com",
    highlighted: false,
  },
];

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1 } },
};

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export function Pricing() {
  const [annual, setAnnual] = useState(false);

  return (
    <section id="pricing" className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            Pricing
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Simple, transparent pricing
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-base" style={{ color: "var(--landing-text-muted)" }}>
            Start free, upgrade when you&apos;re ready. No hidden fees, no surprises.
          </p>

          {/* Toggle */}
          <div className="mt-8 flex items-center justify-center gap-3">
            <span className="text-sm font-medium" style={{ color: annual ? "var(--landing-text-muted)" : "var(--landing-text)" }}>
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className="relative h-6 w-11 rounded-full transition-colors duration-200"
              style={{ backgroundColor: annual ? "var(--landing-accent)" : "var(--landing-border)" }}
              aria-label="Toggle annual pricing"
            >
              <div
                className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-200"
                style={{ left: annual ? "22px" : "2px" }}
              />
            </button>
            <span className="text-sm font-medium" style={{ color: annual ? "var(--landing-text)" : "var(--landing-text-muted)" }}>
              Annual <span style={{ color: "var(--landing-accent)" }}>(-20%)</span>
            </span>
          </div>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="mt-12 grid gap-6 md:grid-cols-3"
        >
          {tiers.map((tier) => (
            <motion.div
              key={tier.name}
              variants={cardVariants}
              whileHover={{ y: -4 }}
              className="relative flex flex-col rounded-2xl border p-8"
              style={{
                borderColor: tier.highlighted ? "var(--landing-accent)" : "var(--landing-border)",
                backgroundColor: "var(--landing-surface)",
                boxShadow: tier.highlighted ? "0 10px 40px var(--landing-accent-glow)" : "none",
              }}
            >
              {tier.highlighted && (
                <div
                  className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-3 py-1 text-xs font-semibold text-white"
                  style={{ backgroundColor: "var(--landing-accent)" }}
                >
                  Most Popular
                </div>
              )}

              <div className="text-lg font-semibold" style={{ color: "var(--landing-text)" }}>{tier.name}</div>
              <p className="mt-1 text-sm" style={{ color: "var(--landing-text-muted)" }}>{tier.description}</p>

              <div className="mt-6">
                <AnimatePresence mode="wait">
                  {tier.monthlyPrice !== null ? (
                    <motion.div
                      key={annual ? "annual" : "monthly"}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      transition={{ duration: 0.2 }}
                    >
                      <span className="text-4xl font-bold tracking-tight" style={{ color: "var(--landing-text)" }}>
                        ${annual ? tier.annualPrice : tier.monthlyPrice}
                      </span>
                      <span className="text-sm" style={{ color: "var(--landing-text-muted)" }}>/mo</span>
                    </motion.div>
                  ) : (
                    <div className="text-4xl font-bold tracking-tight" style={{ color: "var(--landing-text)" }}>
                      Custom
                    </div>
                  )}
                </AnimatePresence>
              </div>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm" style={{ color: "var(--landing-text-muted)" }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--landing-accent)" }}>
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href={tier.ctaLink}
                className="mt-8 flex h-12 items-center justify-center rounded-xl text-sm font-semibold transition-all duration-200"
                style={{
                  backgroundColor: tier.highlighted ? "var(--landing-accent)" : "transparent",
                  color: tier.highlighted ? "white" : "var(--landing-text)",
                  border: tier.highlighted ? "none" : "1px solid var(--landing-border)",
                }}
                onMouseEnter={(e) => {
                  if (tier.highlighted) {
                    e.currentTarget.style.backgroundColor = "var(--landing-accent-hover)";
                  } else {
                    e.currentTarget.style.borderColor = "var(--landing-accent)";
                    e.currentTarget.style.color = "var(--landing-accent)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (tier.highlighted) {
                    e.currentTarget.style.backgroundColor = "var(--landing-accent)";
                  } else {
                    e.currentTarget.style.borderColor = "var(--landing-border)";
                    e.currentTarget.style.color = "var(--landing-text)";
                  }
                }}
              >
                {tier.cta}
              </Link>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 4: Create faq.tsx**

Create `web/components/landing/faq.tsx`:
```tsx
"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

const faqs = [
  {
    question: "How does AI visibility tracking work?",
    answer:
      "We run targeted prompts across ChatGPT, Perplexity, Gemini, and Claude to see how each model responds when asked about your industry, product category, or brand directly. We track mentions, sentiment, citations, and competitor positioning over time.",
  },
  {
    question: "Is Reddit posting automated?",
    answer:
      "No. RedditFlow generates draft replies and posts for you, but all posting is manual. You review, edit, and post from your own Reddit account. This keeps engagement authentic and compliant with Reddit's guidelines.",
  },
  {
    question: "What Reddit rules do you check?",
    answer:
      "Our scoring engine analyzes each subreddit's rules for self-promotion limits, required flair, posting frequency restrictions, account age requirements, and content guidelines. Every opportunity is flagged with rule compliance risks before you engage.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes. All data is encrypted at rest and in transit. Your brand profiles, generated content, and analytics are scoped to your workspace and never shared. We use JWT authentication and workspace-level access controls.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Absolutely. There are no long-term contracts. You can downgrade to the free plan or cancel entirely from your billing settings at any time. Your data remains accessible for 30 days after cancellation.",
  },
  {
    question: "What AI models do you track?",
    answer:
      "We currently track ChatGPT (GPT-4), Perplexity, Google Gemini, and Claude. We're actively adding support for more models and AI-powered search engines as they emerge.",
  },
];

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);

  return (
    <div
      className="border-b"
      style={{ borderColor: "var(--landing-border)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-base font-medium" style={{ color: "var(--landing-text)" }}>
          {question}
        </span>
        <motion.svg
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "var(--landing-text-muted)", flexShrink: 0 }}
        >
          <polyline points="6 9 12 15 18 9" />
        </motion.svg>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <p className="pb-5 text-sm leading-relaxed" style={{ color: "var(--landing-text-muted)" }}>
              {answer}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Faq() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-3xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--landing-accent)" }}
          >
            FAQ
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl"
            style={{ color: "var(--landing-text)" }}
          >
            Frequently asked questions
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="mt-12"
        >
          {faqs.map((faq) => (
            <FaqItem key={faq.question} question={faq.question} answer={faq.answer} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Create final-cta.tsx**

Create `web/components/landing/final-cta.tsx`:
```tsx
"use client";

import Link from "next/link";
import { motion } from "framer-motion";

export function FinalCta() {
  return (
    <section className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="relative overflow-hidden rounded-3xl px-8 py-16 text-center md:px-16 md:py-20"
          style={{
            background: "linear-gradient(135deg, var(--landing-accent) 0%, var(--landing-accent-hover) 100%)",
          }}
        >
          {/* Decorative elements */}
          <div
            className="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full opacity-20"
            style={{ background: "radial-gradient(circle, white 0%, transparent 70%)" }}
          />
          <div
            className="pointer-events-none absolute -bottom-20 -left-20 h-60 w-60 rounded-full opacity-10"
            style={{ background: "radial-gradient(circle, white 0%, transparent 70%)" }}
          />

          <div className="relative">
            <h2 className="text-3xl font-bold tracking-tight text-white md:text-5xl">
              Ready to Own Your AI Visibility?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed" style={{ color: "rgba(255,255,255,0.85)" }}>
              Start tracking how AI models talk about your brand and discover the conversations that shape their answers.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                href="/register"
                className="inline-flex h-12 items-center justify-center rounded-xl bg-white px-8 text-base font-semibold transition-all duration-200"
                style={{ color: "var(--landing-accent)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "scale(1.02)";
                  e.currentTarget.style.boxShadow = "0 10px 40px rgba(0,0,0,0.2)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "scale(1)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                Get Started Free
              </Link>
              <a
                href="mailto:hello@redditflow.com"
                className="inline-flex h-12 items-center justify-center rounded-xl border border-white/30 px-8 text-base font-semibold text-white transition-all duration-200"
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "white";
                  e.currentTarget.style.transform = "scale(1.02)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "rgba(255,255,255,0.3)";
                  e.currentTarget.style.transform = "scale(1)";
                }}
              >
                Schedule Demo
              </a>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
```

- [ ] **Step 6: Create footer.tsx**

Create `web/components/landing/footer.tsx`:
```tsx
"use client";

const footerLinks = {
  Product: ["Features", "Pricing", "Changelog", "Documentation"],
  Company: ["About", "Blog", "Careers", "Contact"],
  Legal: ["Privacy Policy", "Terms of Service", "Cookie Policy"],
};

export function Footer() {
  return (
    <footer
      className="border-t py-12"
      style={{ borderColor: "var(--landing-border)" }}
    >
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-8 md:grid-cols-4">
          {/* Brand */}
          <div>
            <div className="text-lg font-bold tracking-tight" style={{ color: "var(--landing-text)" }}>
              RedditFlow
            </div>
            <p className="mt-2 text-sm" style={{ color: "var(--landing-text-muted)" }}>
              AI visibility and community engagement for modern brands.
            </p>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <div className="mb-3 text-sm font-semibold" style={{ color: "var(--landing-text)" }}>
                {title}
              </div>
              <ul className="space-y-2">
                {links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-sm transition-colors duration-200"
                      style={{ color: "var(--landing-text-muted)" }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "var(--landing-accent)")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "var(--landing-text-muted)")}
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div
          className="mt-12 flex flex-col items-center justify-between gap-4 border-t pt-8 md:flex-row"
          style={{ borderColor: "var(--landing-border)" }}
        >
          <p className="text-xs" style={{ color: "var(--landing-text-muted)" }}>
            &copy; {new Date().getFullYear()} RedditFlow. All rights reserved.
          </p>
          <div className="flex gap-4">
            {["Twitter", "LinkedIn", "Reddit"].map((social) => (
              <a
                key={social}
                href="#"
                className="text-xs transition-colors duration-200"
                style={{ color: "var(--landing-text-muted)" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "var(--landing-accent)")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "var(--landing-text-muted)")}
              >
                {social}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
```

- [ ] **Step 7: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes (components not yet assembled, but must compile without type errors)

- [ ] **Step 8: Commit**

```bash
git add web/components/landing/product-preview.tsx web/components/landing/testimonials.tsx web/components/landing/pricing.tsx web/components/landing/faq.tsx web/components/landing/final-cta.tsx web/components/landing/footer.tsx
git commit -m "feat(landing): add product preview, testimonials, pricing, FAQ, CTA, and footer"
```

---

### Task 10: Assemble Landing Page and Replace page.tsx

**Files:**
- Create: `web/components/landing/index.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Create the main landing page assembler**

Create `web/components/landing/index.tsx`:
```tsx
"use client";

import { LazyMotion, domAnimation } from "framer-motion";
import { Navbar } from "./navbar";
import { Hero } from "./hero";
import { SocialProof } from "./social-proof";
import { HowItWorks } from "./how-it-works";
import { FeatureShowcase } from "./feature-showcase";
import { ProductPreview } from "./product-preview";
import { Testimonials } from "./testimonials";
import { Pricing } from "./pricing";
import { Faq } from "./faq";
import { FinalCta } from "./final-cta";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <LazyMotion features={domAnimation} strict>
      <div className="landing-page">
        <Navbar />
        <main>
          <Hero />
          <SocialProof />
          <HowItWorks />
          <FeatureShowcase />
          <ProductPreview />
          <Testimonials />
          <Pricing />
          <Faq />
          <FinalCta />
        </main>
        <Footer />
      </div>
    </LazyMotion>
  );
}
```

- [ ] **Step 2: Replace page.tsx with thin wrapper**

Replace `web/app/page.tsx` entirely with:
```tsx
import { LandingPage } from "../components/landing";

export default function MarketingPage() {
  return <LandingPage />;
}
```

- [ ] **Step 3: Verify build**

Run:
```bash
cd web && npm run build
```
Expected: Build passes with no TypeScript or compilation errors

- [ ] **Step 4: Commit**

```bash
git add web/components/landing/index.tsx web/app/page.tsx
git commit -m "feat(landing): assemble all sections into landing page and replace page.tsx"
```

---

### Task 11: Visual Verification and Polish

- [ ] **Step 1: Run dev server and visually verify**

Run:
```bash
cd web && npm run dev
```

Open `http://localhost:3000` and verify:
1. Page loads with correct theme (respects system preference)
2. Navbar is sticky with glass blur after scrolling 100px
3. Theme toggle switches between light and dark
4. All 10 sections are present and in correct order
5. Scroll animations trigger as sections enter viewport
6. Social proof counters animate from 0 to target values
7. Pricing toggle switches between monthly/annual
8. FAQ accordion expands/collapses smoothly
9. All hover effects work (buttons, cards, links)
10. Mobile responsive layout at 375px width

- [ ] **Step 2: Run production build**

Run:
```bash
cd web && npm run build
```
Expected: Build succeeds with no warnings

- [ ] **Step 3: Final commit (any polish fixes)**

If any fixes were needed during visual verification:
```bash
git add -u
git commit -m "fix(landing): polish adjustments from visual verification"
```

---

## Self-Review Checklist

**Spec coverage:**
- Theme system (dual light/dark): Task 2 + Task 3 ✓
- Sticky navbar with glass blur: Task 4 ✓
- Hero with stagger + parallax: Task 5 ✓
- Social proof with counters: Task 6 ✓
- How It Works with stagger: Task 7 ✓
- Feature Showcase alternating: Task 8 ✓
- Product Preview with parallax: Task 9 ✓
- Testimonials with stagger: Task 9 ✓
- Pricing with toggle: Task 9 ✓
- FAQ accordion: Task 9 ✓
- Final CTA with gradient: Task 9 ✓
- Footer: Task 9 ✓
- LazyMotion + domAnimation: Task 10 ✓
- Theme toggle via `next-themes` (pre-existing in `layout.tsx`): Task 3 no-op ✓
- Framer Motion + Tailwind deps: Task 1 ✓

**Placeholder scan:** No TBDs, TODOs, or "implement later" found.

**Type consistency:** All components use consistent CSS variable names (`--landing-*`) and import `useTheme` from `next-themes` directly (no custom provider).
