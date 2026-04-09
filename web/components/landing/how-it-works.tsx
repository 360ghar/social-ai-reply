"use client";

import { m } from "framer-motion";

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
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
};

export function HowItWorks() {
  return (
    <section className="py-20 md:py-28">
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
            How It Works
          </span>
          <h2
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl"
          >
            Three steps to AI visibility
          </h2>
        </m.div>

        <m.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-100px" }}
          className="mt-14 grid gap-6 md:grid-cols-3"
        >
          {steps.map((step) => (
            <m.div
              key={step.number}
              variants={cardVariants}
              whileHover={{ y: -4 }}
              transition={{ duration: 0.2 }}
              className="group rounded-2xl border border-border bg-background p-8 transition-shadow duration-300"
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--primary)";
                e.currentTarget.style.boxShadow = "0 10px 40px var(--color-coral-glow)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border)";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div
                className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-coral-glow text-primary"
              >
                {step.icon}
              </div>
              <div
                className="mb-2 text-xs font-bold tracking-wider text-primary"
              >
                STEP {step.number}
              </div>
              <h3
                className="mb-3 text-xl font-semibold tracking-tight text-foreground"
              >
                {step.title}
              </h3>
              <p
                className="text-sm leading-relaxed text-muted-foreground"
              >
                {step.description}
              </p>
            </m.div>
          ))}
        </m.div>
      </div>
    </section>
  );
}
