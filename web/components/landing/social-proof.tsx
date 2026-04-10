"use client";

import { m, useInView } from "framer-motion";
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
      <div className="text-3xl font-bold tracking-tight md:text-4xl text-foreground">
        {count.toLocaleString()}
        {suffix}
      </div>
      <div className="mt-1 text-sm text-muted-foreground">
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
        {/* Desktop grid layout */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="hidden md:grid md:grid-cols-4 gap-8 rounded-2xl border border-border bg-background p-8 md:gap-12"
        >
          {stats.map((stat) => (
            <AnimatedStat key={stat.label} {...stat} />
          ))}
        </m.div>

        {/* Mobile horizontal scroll layout */}
        <m.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="flex gap-4 overflow-x-auto snap-x snap-mandatory pb-4 md:hidden no-scrollbar"
        >
          {stats.map((stat) => (
            <div key={stat.label} className="min-w-[200px] snap-center flex-shrink-0 rounded-2xl border border-border bg-background p-6">
              <AnimatedStat {...stat} />
            </div>
          ))}
        </m.div>
      </div>

      <style jsx>{`
        .no-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .no-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </section>
  );
}
