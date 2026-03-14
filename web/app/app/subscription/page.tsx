"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Subscription } from "../../../lib/api";

type Plan = {
  code: string;
  name: string;
  price_monthly: number;
  features: string[];
  limits: Record<string, number>;
};

function formatStatus(status?: string) {
  const key = (status ?? "trialing").toLowerCase();
  if (key === "trialing") {
    return "Ready";
  }
  if (key === "active") {
    return "Active";
  }
  if (key === "past_due") {
    return "Needs attention";
  }
  if (key === "canceled") {
    return "Canceled";
  }
  return status ?? "Ready";
}

export default function SubscriptionPage() {
  const { token } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [current, setCurrent] = useState<Subscription | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    Promise.all([
      apiRequest<Plan[]>("/v1/billing/plans", {}, token),
      apiRequest<Subscription>("/v1/billing/current", {}, token)
    ])
      .then(([planRows, currentPlan]) => {
        setPlans(planRows);
        setCurrent(currentPlan);
      })
      .catch((err) => setMessage(err.message));
  }, [token]);

  return (
    <section className="card">
      <div className="eyebrow">Plan</div>
      <h2>Your plan and usage limits</h2>
      <p>This page is only about limits and pricing. You can ignore it while setting things up.</p>
      {message ? <div className="notice">{message}</div> : null}
      {current ? (
        <div className="notice">
          Current plan: <strong>{current.plan_code}</strong>. Status: <strong>{formatStatus(current.status)}</strong>.
        </div>
      ) : null}
      <div className="pricing-grid">
        {plans.map((plan) => (
          <div key={plan.code} className="price-card">
            <div className="eyebrow">{plan.name}</div>
            <div className="price">${plan.price_monthly}</div>
            <p>
              {plan.limits.projects} businesses, {plan.limits.keywords} search words, {plan.limits.subreddits} communities.
            </p>
            <div className="item-list">
              {plan.features.map((feature) => (
                <div key={feature} className="list-row">{feature}</div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
