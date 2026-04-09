"use client";

import Link from "next/link";
import { m, AnimatePresence } from "framer-motion";
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
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export function Pricing() {
  const [annual, setAnnual] = useState(false);

  return (
    <section id="pricing" className="py-20 md:py-28">
      <div className="mx-auto max-w-7xl px-6">
        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <span
            className="mb-4 inline-block text-xs font-semibold uppercase tracking-widest text-primary"
          >
            Pricing
          </span>
          <h2
            className="text-3xl font-bold tracking-tight md:text-4xl text-foreground"
          >
            Simple, transparent pricing
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-base text-muted-foreground">
            Start free, upgrade when you&apos;re ready. No hidden fees, no surprises.
          </p>

          <div className="mt-8 flex items-center justify-center gap-3">
            <span className={`text-sm font-medium ${annual ? "text-muted-foreground" : "text-foreground"}`}>
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className={`relative h-6 w-11 rounded-full transition-colors duration-200 ${annual ? "bg-primary" : "bg-border"}`}
              aria-label="Toggle annual pricing"
            >
              <div
                className="absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform duration-200"
                style={{ left: annual ? "22px" : "2px" }}
              />
            </button>
            <span className={`text-sm font-medium ${annual ? "text-foreground" : "text-muted-foreground"}`}>
              Annual <span className="text-primary">(-20%)</span>
            </span>
          </div>
        </m.div>

        <m.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="mt-12 grid gap-6 md:grid-cols-3"
        >
          {tiers.map((tier) => (
            <m.div
              key={tier.name}
              variants={cardVariants}
              whileHover={{ y: -4 }}
              className={`relative flex flex-col rounded-2xl border p-8 ${tier.highlighted ? "border-primary" : "border-border"} bg-background`}
              style={{
                boxShadow: tier.highlighted ? "0 10px 40px var(--color-coral-glow)" : "none",
              }}
            >
              {tier.highlighted && (
                <div
                  className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-white"
                >
                  Most Popular
                </div>
              )}

              <div className="text-lg font-semibold text-foreground">{tier.name}</div>
              <p className="mt-1 text-sm text-muted-foreground">{tier.description}</p>

              <div className="mt-6">
                <AnimatePresence mode="wait">
                  {tier.monthlyPrice !== null ? (
                    <m.div
                      key={annual ? "annual" : "monthly"}
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      transition={{ duration: 0.2 }}
                    >
                      <span className="text-4xl font-bold tracking-tight text-foreground">
                        ${annual ? tier.annualPrice : tier.monthlyPrice}
                      </span>
                      <span className="text-sm text-muted-foreground">/mo</span>
                    </m.div>
                  ) : (
                    <div className="text-4xl font-bold tracking-tight text-foreground">
                      Custom
                    </div>
                  )}
                </AnimatePresence>
              </div>

              <ul className="mt-6 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--primary)" }}>
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>

              <Link
                href={tier.ctaLink}
                className={`mt-8 flex h-12 items-center justify-center rounded-xl text-sm font-semibold transition-all duration-200 ${
                  tier.highlighted
                    ? "bg-primary text-white border-none hover:bg-[var(--color-coral-hover)]"
                    : "bg-transparent text-foreground border border-border hover:border-primary hover:text-primary"
                }`}
              >
                {tier.cta}
              </Link>
            </m.div>
          ))}
        </m.div>
      </div>
    </section>
  );
}
