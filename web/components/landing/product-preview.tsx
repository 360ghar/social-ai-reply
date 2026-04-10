"use client";

import { m, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";

export function ProductPreview() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [20, -20]);

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
            Product
          </span>
          <h2
            className="text-3xl font-bold tracking-tight text-foreground md:text-4xl"
          >
            Your AI command center
          </h2>
          <p
            className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground"
          >
            One dashboard to track AI visibility, discover opportunities, and generate content — all in real time.
          </p>
        </m.div>

        <m.div
          ref={ref}
          style={{ y }}
          className="mx-auto mt-12 max-w-5xl"
        >
          <div
            className="overflow-hidden rounded-2xl border border-border shadow-lg"
          >
            <div className="p-1">
              <div className="rounded-xl bg-background p-6">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  <div className="col-span-1 space-y-3">
                    <div className="rounded-lg bg-muted p-3">
                      <div className="text-xs font-semibold text-foreground">Workspace</div>
                      <div className="mt-2 space-y-1.5">
                        {["Dashboard", "Visibility", "Discovery", "Content", "Analytics"].map((item, i) => (
                          <div key={item} className="rounded px-2 py-1 text-xs" style={{
                            backgroundColor: i === 0 ? "var(--color-coral-glow)" : "transparent",
                            color: i === 0 ? "var(--primary)" : "var(--muted-foreground)",
                            fontWeight: i === 0 ? 600 : 400,
                          }}>
                            {item}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-lg bg-muted p-3">
                      <div className="text-xs font-semibold text-foreground">Active Project</div>
                      <div className="mt-1 text-xs text-muted-foreground">Acme Corp</div>
                      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-border">
                        <div className="h-full rounded-full bg-primary" style={{ width: "78%" }} />
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">78% profile complete</div>
                    </div>
                  </div>
                  <div className="col-span-2 space-y-3">
                    <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                      {[
                        { label: "Visibility Score", value: "87", change: "+12%" },
                        { label: "Opportunities", value: "142", change: "+28" },
                        { label: "Drafts Ready", value: "38", change: "+9" },
                      ].map((kpi) => (
                        <div key={kpi.label} className="rounded-lg bg-muted p-3">
                          <div className="text-xs text-muted-foreground">{kpi.label}</div>
                          <div className="mt-1 text-xl font-bold text-foreground">{kpi.value}</div>
                          <div className="mt-0.5 text-xs font-medium text-primary">{kpi.change}</div>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-lg bg-muted p-3">
                      <div className="mb-2 text-xs font-semibold text-foreground">Top Opportunities</div>
                      <div className="space-y-1.5">
                        {[
                          { sub: "r/SaaS", post: "Best CRM for startups 2025?", score: 94 },
                          { sub: "r/Marketing", post: "HubSpot alternatives that don't break the bank", score: 89 },
                          { sub: "r/SmallBusiness", post: "What CRM do you use and why?", score: 85 },
                        ].map((opp) => (
                          <div key={opp.post} className="flex items-center justify-between rounded px-2 py-1.5">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-medium text-muted-foreground">{opp.sub}</span>
                              <span className="text-xs text-foreground">{opp.post}</span>
                            </div>
                            <span className="rounded-full bg-coral-glow px-2 py-0.5 text-xs font-bold text-primary">{opp.score}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </m.div>
      </div>
    </section>
  );
}
