export function formatPlan(planCode?: string): string {
  const key = (planCode ?? "free").toLowerCase();
  if (key === "free") {
    return "Free plan";
  }
  if (key === "starter") {
    return "Starter";
  }
  if (key === "growth") {
    return "Growth";
  }
  return planCode ?? "Free plan";
}

export function formatStatus(status?: string): string {
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
