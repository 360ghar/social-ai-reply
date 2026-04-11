import { apiRequest } from "../api";

import type { Subscription } from "../api";

export type { Subscription };

export interface Plan {
  code: string;
  name: string;
  price_monthly: number;
  features: string[];
  limits: Record<string, number>;
}

export interface RedemptionResult {
  success: boolean;
  plan_code: string;
  message: string;
}

export async function getPlans(token: string): Promise<Plan[]> {
  return apiRequest<Plan[]>("/v1/billing/plans", {}, token);
}

export async function getCurrentSubscription(token: string): Promise<Subscription> {
  return apiRequest<Subscription>("/v1/billing/current", {}, token);
}

export async function upgradePlan(token: string, planCode: string): Promise<Subscription> {
  return apiRequest<Subscription>(
    "/v1/billing/upgrade",
    { method: "POST", body: JSON.stringify({ plan_code: planCode }) },
    token,
  );
}

export async function redeemCode(token: string, code: string): Promise<RedemptionResult> {
  return apiRequest<RedemptionResult>(
    "/v1/redemptions",
    { method: "POST", body: JSON.stringify({ code }) },
    token,
  );
}
