"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Loader2, Sparkles, Tag } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { useToast } from "@/stores/toast";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress, ProgressIndicator, ProgressTrack } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import {
  getCurrentSubscription,
  getPlans,
  redeemCode,
  upgradePlan,
  type Plan,
  type Subscription,
} from "@/lib/api/billing";
import { getUsage, type UsageResponse } from "@/lib/api/workspace";

const UNLIMITED_SENTINEL = 999999;

function formatLimit(limit: number): string {
  if (!Number.isFinite(limit) || limit >= UNLIMITED_SENTINEL) return "Unlimited";
  return limit.toLocaleString();
}

function formatMetricKey(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, " ");
}

function formatPrice(price: number): string {
  if (price === 0) return "Free";
  return `$${price}/mo`;
}

export default function SubscriptionPage() {
  const { token } = useAuth();
  const projectId = useSelectedProjectId();
  const toast = useToast();

  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [redeemLoading, setRedeemLoading] = useState(false);
  const [redeemCodeValue, setRedeemCodeValue] = useState("");

  const loadBilling = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [plansRes, subRes, usageRes] = await Promise.all([
        getPlans(token),
        getCurrentSubscription(token),
        getUsage(token, projectId ?? undefined).catch(() => null),
      ]);
      setPlans(plansRes);
      setSubscription(subRes);
      setUsage(usageRes);
    } catch (err) {
      toast.error("Failed to load subscription", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
    // loadBilling is intentionally decoupled from toast identity (stable toast methods)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, projectId]);

  useEffect(() => {
    void loadBilling();
  }, [loadBilling]);

  const currentPlan = useMemo(
    () => plans.find((p) => p.code === subscription?.plan_code) ?? null,
    [plans, subscription],
  );

  async function handleUpgrade(planCode: string) {
    if (!token) return;
    if (planCode === subscription?.plan_code) return;
    setUpgrading(planCode);
    try {
      const updated = await upgradePlan(token, planCode);
      setSubscription(updated);
      toast.success("Plan updated", `You're now on the ${planCode} plan.`);
    } catch (err) {
      toast.error("Upgrade failed", err instanceof Error ? err.message : undefined);
    } finally {
      setUpgrading(null);
    }
  }

  async function handleRedeem(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    const code = redeemCodeValue.trim();
    if (!code) {
      toast.warning("Enter a code", "Paste the redemption code to continue.");
      return;
    }
    setRedeemLoading(true);
    try {
      const result = await redeemCode(token, code);
      toast.success("Code redeemed", result.message ?? `Plan: ${result.plan_code}`);
      setRedeemCodeValue("");
      await loadBilling();
    } catch (err) {
      toast.error("Redemption failed", err instanceof Error ? err.message : undefined);
    } finally {
      setRedeemLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="Subscription"
        description="Manage your plan, view usage, and redeem access codes."
      />

      {loading ? (
        <div className="grid gap-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <>
          <CurrentPlanCard subscription={subscription} currentPlan={currentPlan} />

          <UsageSection usage={usage} />

          <section>
            <h3 className="mb-4 text-sm font-semibold text-foreground">Available plans</h3>
            <div className="grid gap-4 md:grid-cols-2">
              {plans.map((plan) => {
                const isCurrent = plan.code === subscription?.plan_code;
                const isBusy = upgrading === plan.code;
                return (
                  <Card key={plan.code} className={isCurrent ? "ring-2 ring-primary" : undefined}>
                    <CardHeader>
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            {plan.name}
                            {isCurrent && (
                              <Badge variant="default" className="text-xs">
                                Current
                              </Badge>
                            )}
                          </CardTitle>
                          <CardDescription className="mt-1 text-lg font-semibold text-foreground">
                            {formatPrice(plan.price_monthly)}
                          </CardDescription>
                        </div>
                        <Sparkles className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                      <ul className="grid gap-2 text-sm">
                        {plan.features.map((feature) => (
                          <li key={feature} className="flex items-start gap-2">
                            <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                            <span>{feature}</span>
                          </li>
                        ))}
                      </ul>
                      <Separator />
                      <dl className="grid gap-1.5 text-xs text-muted-foreground">
                        {Object.entries(plan.limits).map(([key, value]) => (
                          <div key={key} className="flex items-center justify-between">
                            <dt className="capitalize">{formatMetricKey(key)}</dt>
                            <dd className="tabular-nums text-foreground">{formatLimit(value)}</dd>
                          </div>
                        ))}
                      </dl>
                      <Button
                        variant={isCurrent ? "outline" : "default"}
                        onClick={() => handleUpgrade(plan.code)}
                        disabled={isCurrent || isBusy}
                        aria-label={isCurrent ? `${plan.name} is your current plan` : `Switch to ${plan.name}`}
                      >
                        {isBusy && <Loader2 className="h-4 w-4 animate-spin" />}
                        {isCurrent ? "Your current plan" : `Switch to ${plan.name}`}
                      </Button>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </section>

          <section className="rounded-lg border border-border bg-muted/30 p-5">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Tag className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-foreground">Redeem a code</h3>
                <p className="text-xs text-muted-foreground">
                  Have a coupon or access code? Enter it below to unlock features.
                </p>
                <form onSubmit={handleRedeem} className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="grid flex-1 gap-2">
                    <Label htmlFor="redeem-code">Redemption code</Label>
                    <Input
                      id="redeem-code"
                      value={redeemCodeValue}
                      onChange={(event) => setRedeemCodeValue(event.target.value)}
                      placeholder="e.g., LAUNCH-2026"
                      disabled={redeemLoading}
                    />
                  </div>
                  <Button type="submit" disabled={redeemLoading || !redeemCodeValue.trim()}>
                    {redeemLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                    Redeem
                  </Button>
                </form>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function CurrentPlanCard({
  subscription,
  currentPlan,
}: {
  subscription: Subscription | null;
  currentPlan: Plan | null;
}) {
  const periodEnd = subscription?.current_period_end
    ? new Date(subscription.current_period_end).toLocaleDateString()
    : null;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Current plan</CardTitle>
            <CardDescription>Your active subscription and billing status.</CardDescription>
          </div>
          {subscription?.status && (
            <Badge variant={subscription.status === "active" ? "default" : "secondary"}>
              {subscription.status}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {subscription ? (
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricBlock label="Plan" value={currentPlan?.name ?? subscription.plan_code} />
            <MetricBlock
              label="Price"
              value={currentPlan ? formatPrice(currentPlan.price_monthly) : "—"}
            />
            <MetricBlock label="Renews" value={periodEnd ?? "—"} />
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No subscription found.</p>
        )}
      </CardContent>
    </Card>
  );
}

function MetricBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}

function UsageSection({ usage }: { usage: UsageResponse | null }) {
  if (!usage) {
    return null;
  }
  const metricEntries = Object.entries(usage.metrics);
  return (
    <section>
      <h3 className="mb-4 text-sm font-semibold text-foreground">Usage</h3>
      {metricEntries.length === 0 ? (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            No usage metrics recorded yet.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {metricEntries.map(([key, { used, limit }]) => {
            const unlimited = !Number.isFinite(limit) || limit >= UNLIMITED_SENTINEL;
            const percent = unlimited ? 0 : Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));
            return (
              <Card key={key} size="sm">
                <CardContent className="flex flex-col gap-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium capitalize">{formatMetricKey(key)}</span>
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {used.toLocaleString()} / {formatLimit(limit)}
                    </span>
                  </div>
                  <Progress value={unlimited ? null : percent}>
                    <ProgressTrack>
                      <ProgressIndicator />
                    </ProgressTrack>
                  </Progress>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </section>
  );
}
