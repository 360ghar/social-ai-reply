# Landing Page Redesign — Design Spec

**Date**: 2026-04-09
**Status**: Approved

## Context

The current landing page (`web/app/page.tsx`) is a 718-line server component with zero animations, mostly inline styles, and no scroll effects. It doesn't convey the premium, trust-building feel of a billion-dollar AI company. This redesign transforms it into a modern, animated landing page with dual-theme support, scroll animations, and a polished 10-section architecture.

## Technical Stack

- **New dependencies**: `framer-motion`, `tailwindcss`, `@tailwindcss/postcss` (PostCSS plugin for Next.js 16)
- **Styling**: Tailwind CSS utility classes (new landing page) + existing CSS files unchanged for rest of app
- **Animations**: Framer Motion with `LazyMotion` + `domAnimation` for bundle optimization
- **Fonts**: Inter (variable) + JetBrains Mono via `next/font/google`

## Theme System

CSS custom properties on `:root` (light default) and `[data-theme="dark"]`:

| Token | Light | Dark |
|-------|-------|------|
| Background | `#fafafa` | `#0a0a0b` |
| Surface | `#ffffff` | `#141416` |
| Card | `#f4f4f5` | `#1a1a1f` |
| Border | `#e4e4e7` | `#2a2a30` |
| Text primary | `#09090b` | `#fafafa` |
| Text muted | `#71717a` | `#a1a1aa` |
| Accent | `#FF6B6B` → `#FF4757` | same |
| Accent hover | `#FF4757` | same |

**ThemeProvider**: Client component reading/writing `localStorage`, toggling `data-theme` attribute on `<html>`. Respects `prefers-color-scheme` as default.

## Typography

- Primary: Inter variable via `next/font/google`
- Monospace: JetBrains Mono for stats/numbers
- Headlines: `clamp(2.5rem, 5vw, 4.5rem)`, tracking `-0.03em`, weight 700
- Section headings: `clamp(1.75rem, 3vw, 2.5rem)`, tracking `-0.02em`
- Body: 16-18px, line-height 1.6, weight 400
- Eyebrow/label: 14px, uppercase, tracking `0.08em`, weight 600

## Page Architecture (10 sections)

### 1. Sticky Navbar
- **Behavior**: Transparent over hero → frosted glass (`backdrop-filter: blur(12px)`) after 100px scroll via `useScroll` threshold
- **Layout**: Logo left, nav links center (Features, Pricing, Testimonials), CTA button right + theme toggle
- **Animation**: Background opacity transition on scroll
- **File**: `web/components/landing/navbar.tsx`

### 2. Hero Section
- **Layout**: Centered text — eyebrow label "AI Visibility Platform", headline, subtitle, two CTAs ("Start Free Trial" primary, "Watch Demo" secondary)
- **Below fold**: Product screenshot/mockup with subtle parallax float (max 30px translateY linked to scroll)
- **Animation**: Stagger — headline fades up (0ms) → subtitle (100ms) → buttons (200ms) → screenshot (300ms). All `whileInView` with `once: true`
- **Copy**:
  - Headline: "See How AI Talks About Your Brand"
  - Subtitle: "RedditFlow tracks your brand across ChatGPT, Perplexity, Gemini, and Claude — then finds the Reddit conversations that shape what they say."
- **File**: `web/components/landing/hero.tsx`

### 3. Social Proof Bar
- **Layout**: Full-width row with 4 stat blocks, each with a large number + label
- **Stats**: "500+ Brands Tracked" | "1M+ Posts Analyzed" | "4 AI Models Monitored" | "98% Uptime"
- **Animation**: Counter animation — numbers count from 0 to target over 2 seconds using Framer Motion's `useSpring` when scrolled into view
- **File**: `web/components/landing/social-proof.tsx`

### 4. How It Works
- **Layout**: 3-column grid with numbered step icons
- **Steps**:
  1. "Connect Your Brand" — Enter your website. Our AI builds a complete profile of your business, audience, and voice.
  2. "Track AI Visibility" — See how ChatGPT, Perplexity, Gemini, and Claude mention your brand. Spot gaps where competitors appear instead.
  3. "Engage Authentically" — Discover high-intent Reddit conversations and draft helpful, brand-aware replies — never spammy.
- **Animation**: Staggered reveal — each card fades up 100ms after previous
- **File**: `web/components/landing/how-it-works.tsx`

### 5. Feature Showcase (3 sections, alternating)
Each feature section alternates layout (text-left/image-right, then text-right/image-left):

**Feature 1 — "AI Visibility Dashboard"**
- Description: "Track brand mentions across every major AI model with sentiment analysis and citation tracking."
- Visual: Dashboard mockup showing visibility scores, AI model comparison
- Layout: Text left, image right

**Feature 2 — "Smart Opportunity Discovery"**
- Description: "AI-powered scoring finds the Reddit conversations where your expertise matters most."
- Visual: Opportunity cards with relevance scores and fit indicators
- Layout: Text right, image left

**Feature 3 — "Brand-Aware Content Studio"**
- Description: "Generate authentic replies and posts that match your voice, checked against subreddit rules."
- Visual: Draft editor with brand voice alignment indicators
- Layout: Text left, image right

- **Animation**: Each section uses `whileInView` fade-up for text and slide-in for image
- **Files**: `web/components/landing/feature-showcase.tsx`

### 6. Product Screenshots
- **Layout**: Full-width dashboard mockup with callout annotations pointing to key UI elements
- **Animation**: Subtle parallax float effect
- **File**: `web/components/landing/product-preview.tsx`

### 7. Testimonials
- **Layout**: 3-column grid of testimonial cards
- **Each card**: Quote text, avatar placeholder, name, role, company
- **Animation**: Staggered fade-up, each card 150ms after previous
- **File**: `web/components/landing/testimonials.tsx`

### 8. Pricing
- **Layout**: 3-tier cards (Free, Pro, Enterprise) with monthly/annual toggle
- **Tiers**:
  - Free: "$0/mo" — 1 project, 50 scans/mo, basic visibility tracking, community support
  - Pro: "$49/mo" — 5 projects, 500 scans/mo, full visibility suite, content studio, priority support
  - Enterprise: "Contact us" — Unlimited projects, unlimited scans, custom integrations, dedicated support, SLA
- **CTAs**: "Get Started" (Free/Pro), "Schedule Demo" (Enterprise)
- **Animation**: Cards stagger in from bottom
- **File**: `web/components/landing/pricing.tsx`

### 9. FAQ
- **Layout**: Accordion — click to expand/collapse
- **Questions** (6-8): How does AI visibility work? Is posting automated? What Reddit rules do you check? Is my data secure? Can I cancel anytime? What AI models do you track?
- **Animation**: Smooth height animation on expand/collapse via Framer Motion `AnimatePresence`
- **File**: `web/components/landing/faq.tsx`

### 10. Final CTA
- **Layout**: Full-width section with coral gradient background
- **Content**: Headline "Ready to Own Your AI Visibility?" + subtitle + single "Get Started Free" button
- **Animation**: Fade-in on scroll
- **File**: `web/components/landing/final-cta.tsx`

## Animation Specification

| Pattern | Usage | Config |
|---------|-------|--------|
| `whileInView` fade-up | All sections | `y: 40 → 0`, `opacity: 0 → 1`, `duration: 0.6`, `once: true` |
| Stagger children | Cards, steps, testimonials | `staggerChildren: 0.1`, each child: `y: 30 → 0` |
| Counter animation | Social proof stats | `useSpring` from 0 to target, `duration: 2` |
| Parallax float | Hero screenshot, product preview | `useScroll` + `useTransform`, max 30px translateY |
| Navbar scroll | Sticky nav | `useScroll` threshold at 100px, toggle glass effect |
| Hover — buttons | CTAs | `scale: 1.02`, `backgroundColor` shift |
| Hover — cards | Feature, pricing, testimonial | `y: -4px`, `boxShadow` expansion |
| Hover — links | Nav links, inline links | Underline slides in from left (`originX: 0`) |

**Performance**: `LazyMotion` with `domAnimation` wrapper. Only `transform` and `opacity` animated. `useReducedMotion` check — skip animations if user prefers reduced motion.

## File Structure

```
web/
├── app/
│   └── page.tsx                          # Simplified: imports and renders LandingPage client component
├── components/
│   └── landing/
│       ├── index.tsx                      # Main LandingPage client component (assembles all sections)
│       ├── navbar.tsx                     # Sticky nav with glass blur
│       ├── hero.tsx                       # Hero section
│       ├── social-proof.tsx               # Stats counter bar
│       ├── how-it-works.tsx               # 3-step process
│       ├── feature-showcase.tsx           # 3 alternating feature sections
│       ├── product-preview.tsx            # Full-width product screenshot
│       ├── testimonials.tsx               # Customer quotes
│       ├── pricing.tsx                    # 3-tier pricing cards
│       ├── faq.tsx                        # Accordion FAQ
│       ├── final-cta.tsx                  # Bottom CTA section
│       ├── theme-provider.tsx             # Theme toggle + persistence
│       └── footer.tsx                     # Footer
├── styles/
│   └── landing.css                        # Tailwind @import + custom CSS vars + landing-specific styles
```

## Existing Files Modified

- `web/app/page.tsx` — Replace with a thin wrapper importing the new landing component
- `web/app/layout.tsx` — Add ThemeProvider wrapper + Tailwind CSS import
- `web/package.json` — Add `framer-motion`, `tailwindcss`, `@tailwindcss/postcss`
- `web/postcss.config.mjs` — Add Tailwind PostCSS plugin (new file)
- `web/styles/globals.css` — Add theme CSS custom properties

## Verification

1. `npm run dev` — Landing page loads without errors
2. Scroll through all 10 sections — each animates on entry
3. Toggle light/dark theme — all sections update correctly
4. Resize to mobile (375px) — responsive layout works
5. Check `prefers-reduced-motion` — animations disabled
6. `npm run build` — TypeScript + production build passes
7. Lighthouse audit — Performance > 90, Accessibility > 95
