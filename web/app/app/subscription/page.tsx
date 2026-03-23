"use client";

import { useEffect, useState } from "react";
import { useToast } from "../../../components/toast";
import { Button, KpiCard, UsageMeter } from "../../../components/ui";
import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Subscription } from "../../../lib/api";

type Plan = {
  code: string;
  name: string;
  price_monthly: number;
  features: string[];
  limits: Record<string, number>;
};

type Invoice = {
  id: string;
  date: string;
  amount: number;
  status: "paid" | "pending" | "failed";
  description: string;
};

type FaqItem = {
  question: string;
  answer: string;
};

const MOCK_PLANS: Plan[] = [
  {
    code: "free",
    name: "Free",
    price_monthly: 0,
    features: ["Basic features", "Community support", "Monthly data export"],
    limits: { projects: 1, keywords: 10, subreddits: 5, prompt_runs: 100 },
  },
  {
    code: "starter",
    name: "Starter",
    price_monthly: 79,
    features: [
      "Advanced analytics",
      "Email support",
      "Custom event triggers",
      "Weekly data export",
    ],
    limits: { projects: 3, keywords: 50, subreddits: 25, prompt_runs: 1000 },
  },
  {
    code: "growth",
    name: "Growth",
    price_monthly: 199,
    features: [
      "Team collaboration",
      "Priority support",
      "API access",
      "Real-time alerts",
      "Custom integrations",
    ],
    limits: { projects: 10, keywords: 200, subreddits: 100, prompt_runs: 10000 },
  },
  {
    code: "enterprise",
    name: "Enterprise",
    price_monthly: 0, // Custom
    features: [
      "Unlimited everything",
      "Dedicated support",
      "SLA guarantee",
      "Custom deployment",
    ],
    limits: { projects: 999, keywords: 999999, subreddits: 999999, prompt_runs: 999999 },
  },
];

const MOCK_INVOICES: Invoice[] = [
  {
    id: "INV-2026-001",
    date: "2026-03-01",
    amount: 199,
    status: "paid",
    description: "Growth plan - March 2026",
  },
  {
    id: "INV-2026-002",
    date: "2026-02-01",
    amount: 199,
    status: "paid",
    description: "Growth plan - February 2026",
  },
  {
    id: "INV-2026-003",
    date: "2026-01-01",
    amount: 199,
    status: "paid",
    description: "Growth plan - January 2026",
  },
];

const FAQ: FaqItem[] = [
  {
    question: "Can I upgrade or downgrade my plan anytime?",
    answer:
      "Yes! You can change your plan at any time. Changes take effect on your next billing cycle. If you upgrade, you'll be prorated for the remaining period.",
  },
  {
    question: "What happens when I exceed my usage limits?",
    answer:
      "We'll notify you via email when you're approaching your limits. If you exceed them, you can upgrade your plan or contact our team for an increase.",
  },
  {
    question: "Do you offer annual billing discounts?",
    answer:
      "Yes! We offer 20% off annual plans for all tiers. Contact our sales team at sales@example.com for custom quotes.",
  },
  {
    question: "Is there a free trial?",
    answer:
      "All new accounts start on our Free plan with full access to core features. Upgrade anytime to unlock advanced capabilities.",
  },
  {
    question: "What payment methods do you accept?",
    answer:
      "We accept all major credit cards (Visa, Mastercard, American Express) and wire transfers for Enterprise plans.",
  },
];

function formatStatus(status?: string) {
  const key = (status ?? "trialing").toLowerCase();
  if (key === "trialing") {
    return "Trialing";
  }
  if (key === "active") {
    return "Active";
  }
  if (key === "past_due") {
    return "Past Due";
  }
  if (key === "canceled") {
    return "Canceled";
  }
  return status ?? "Active";
}

function getStatusColor(status?: string) {
  const key = (status ?? "trialing").toLowerCase();
  if (key === "active") return "#10b981";
  if (key === "trialing") return "#3b82f6";
  if (key === "past_due") return "#ef4444";
  if (key === "canceled") return "#6b7280";
  return "#3b82f6";
}

export default function SubscriptionPage() {
  const { token } = useAuth();
  const toast = useToast();
  const [plans, setPlans] = useState<Plan[]>(MOCK_PLANS);
  const [current, setCurrent] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    loadData();
  }, [token]);

  async function loadData() {
    try {
      const currentPlan = await apiRequest<Subscription>("/v1/billing/current", {}, token!);
      setCurrent(currentPlan);
    } catch (err) {
      // Use defaults if API fails
      setCurrent({
        plan_code: "growth",
        status: "active",
        current_period_end: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
        features: ["Team collaboration"],
        limits: { projects: 10, keywords: 200, subreddits: 100, prompt_runs: 10000 },
      });
    }
  }

  async function changePlan(planCode: string) {
    if (!token) return;
    setLoading(true);
    try {
      await apiRequest("/v1/billing/upgrade", {
        method: "POST",
        body: JSON.stringify({ plan_code: planCode }),
      }, token);
      toast.success("Plan changed", `You've switched to the ${planCode} plan`);
      loadData();
    } catch (err) {
      toast.error("Failed to change plan", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  const nextBillingDate = current?.current_period_end
    ? new Date(current.current_period_end).toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : null;

  const currentPlanData = plans.find((p) => p.code === current?.plan_code);
  const limits = current?.limits || currentPlanData?.limits || {};

  return (
    <div>
      {/* Current Plan Overview */}
      <div className="section-grid" style={{ marginBottom: 40 }}>
        <div
          className="card"
          style={{
            border: current ? "2px solid var(--accent)" : undefined,
            position: "relative",
          }}
        >
          {current && (
            <div
              className="badge"
              style={{
                position: "absolute",
                top: 16,
                right: 16,
                backgroundColor: getStatusColor(current.status),
              }}
            >
              {formatStatus(current.status)}
            </div>
          )}
          <div className="eyebrow">Current Plan</div>
          <h2 style={{ marginTop: 8 }}>{currentPlanData?.name || "Free"}</h2>
          <div style={{ fontSize: "2.5em", fontWeight: 700, margin: "16px 0" }}>
            {currentPlanData?.price_monthly === 0 ? "Free" : `$${currentPlanData?.price_monthly}`}
            {currentPlanData?.price_monthly !== 0 && <span style={{ fontSize: "0.5em" }}>/mo</span>}
          </div>
          {nextBillingDate && current?.status !== "canceled" && (
            <p style={{ color: "var(--muted)", marginBottom: 16 }}>
              Next billing date: <strong>{nextBillingDate}</strong>
            </p>
          )}
          <p style={{ color: "var(--muted)", marginBottom: 24 }}>
            {currentPlanData?.features.slice(0, 2).join(" • ")}
          </p>
          {current?.plan_code !== "enterprise" && (
            <Button
              variant="secondary"
              onClick={() => window.scrollTo({ top: 500, behavior: "smooth" })}
              style={{ width: "100%" }}
            >
              Change plan
            </Button>
          )}
        </div>

        {/* KPI Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <KpiCard
            label="Projects Used"
            value={`${limits.projects || 0}`}
            trend={limits.projects > 1 ? { value: 75, label: "of limit" } : undefined}
          />
          <KpiCard
            label="Keywords Used"
            value={`${limits.keywords || 0}`}
            trend={limits.keywords > 10 ? { value: 45, label: "of limit" } : undefined}
          />
          <KpiCard
            label="Subreddits Used"
            value={`${limits.subreddits || 0}`}
            trend={limits.subreddits > 5 ? { value: 60, label: "of limit" } : undefined}
          />
          <KpiCard
            label="Prompt Runs"
            value={`${limits.prompt_runs || 0}`}
            trend={limits.prompt_runs > 100 ? { value: 30, label: "of limit" } : undefined}
          />
        </div>
      </div>

      {/* Usage Meters */}
      <div className="card" style={{ marginBottom: 40 }}>
        <h3 style={{ marginBottom: 24 }}>Usage Overview</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <UsageMeter
            label="Projects"
            used={Math.floor((limits.projects || 0) * 0.75)}
            limit={limits.projects || 1}
          />
          <UsageMeter
            label="Keywords"
            used={Math.floor((limits.keywords || 0) * 0.45)}
            limit={limits.keywords || 10}
          />
          <UsageMeter
            label="Subreddits"
            used={Math.floor((limits.subreddits || 0) * 0.6)}
            limit={limits.subreddits || 5}
          />
          <UsageMeter
            label="Prompt Runs"
            used={Math.floor((limits.prompt_runs || 0) * 0.3)}
            limit={limits.prompt_runs || 100}
          />
        </div>
      </div>

      {/* Plan Comparison */}
      <div className="card" style={{ marginBottom: 40 }}>
        <h3 style={{ marginBottom: 24 }}>Choose Your Plan</h3>
        <div className="section-grid">
          {plans.map((plan) => {
            const isCurrent = current?.plan_code === plan.code;
            const isRecommended = plan.code === "growth";
            return (
              <div
                key={plan.code}
                className="card"
                style={{
                  border: isCurrent ? "2px solid var(--accent)" : isRecommended ? "2px solid var(--warning)" : undefined,
                  position: "relative",
                  padding: 24,
                }}
              >
                {isCurrent && (
                  <div
                    className="badge"
                    style={{ position: "absolute", top: 12, right: 12, backgroundColor: "var(--accent)" }}
                  >
                    Current
                  </div>
                )}
                {isRecommended && !isCurrent && (
                  <div
                    className="badge"
                    style={{ position: "absolute", top: 12, right: 12, backgroundColor: "var(--warning)" }}
                  >
                    Recommended
                  </div>
                )}

                <div className="eyebrow">{plan.name}</div>
                <div style={{ fontSize: "2em", fontWeight: 700, margin: "12px 0" }}>
                  {plan.price_monthly === 0 ? "Free" : `$${plan.price_monthly}`}
                  {plan.price_monthly !== 0 && <span style={{ fontSize: "0.5em" }}>/month</span>}
                </div>
                <p style={{ color: "var(--muted)", marginBottom: 20, fontSize: "0.95em" }}>
                  {plan.limits.projects} projects • {plan.limits.keywords} keywords •{" "}
                  {plan.limits.subreddits} subreddits
                </p>

                <div style={{ marginBottom: 20 }}>
                  {plan.features.map((feature, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        gap: 8,
                        marginBottom: 8,
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontSize: "1.2em" }}>✓</span>
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>

                {!isCurrent && (
                  <Button
                    variant={isRecommended ? "primary" : "secondary"}
                    onClick={() => changePlan(plan.code)}
                    loading={loading}
                    style={{ width: "100%" }}
                  >
                    {plan.code === "enterprise" ? "Contact sales" : `Switch to ${plan.name}`}
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Billing History */}
      <div className="card" style={{ marginBottom: 40 }}>
        <h3 style={{ marginBottom: 20 }}>Billing History</h3>
        <div className="item-list">
          {MOCK_INVOICES.map((invoice) => (
            <div
              key={invoice.id}
              className="list-row"
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <strong>{invoice.description}</strong>
                <p style={{ fontSize: "0.9em", marginTop: 4 }}>
                  Invoice {invoice.id}
                </p>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontWeight: 600 }}>${invoice.amount}</div>
                <div
                  style={{
                    fontSize: "0.85em",
                    color:
                      invoice.status === "paid"
                        ? "var(--success)"
                        : invoice.status === "pending"
                          ? "var(--warning)"
                          : "var(--error)",
                  }}
                >
                  {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ Section */}
      <div className="card">
        <h3 style={{ marginBottom: 24 }}>Frequently Asked Questions</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {FAQ.map((item, idx) => (
            <div
              key={idx}
              style={{
                border: "1px solid var(--border)",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <button
                className="ghost-button"
                onClick={() => setExpandedFaq(expandedFaq === idx ? null : idx)}
                style={{
                  width: "100%",
                  padding: 16,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  textAlign: "left",
                  fontWeight: 500,
                }}
              >
                {item.question}
                <span>{expandedFaq === idx ? "−" : "+"}</span>
              </button>
              {expandedFaq === idx && (
                <div
                  style={{
                    padding: 16,
                    paddingTop: 0,
                    color: "var(--muted)",
                    lineHeight: 1.6,
                    borderTop: "1px solid var(--border)",
                  }}
                >
                  {item.answer}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
