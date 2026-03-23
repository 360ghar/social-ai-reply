"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import {
  Button,
  EmptyState,
  KpiCard,
  StepIndicator,
  UsageMeter,
  Spinner,
  ScoreBadge,
  PlatformIcon,
  SkeletonCard,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";

interface SetupStatus {
  brand_configured: boolean;
  personas_count: number;
  subreddits_count: number;
}

interface DashData {
  projects: any[];
  top_opportunities: any[];
  subscription: any;
  setup_status?: SetupStatus;
}

interface UsageData {
  plan?: string;
  metrics?: {
    projects?: { used: number; limit: number };
    keywords?: { used: number; limit: number };
    subreddits?: { used: number; limit: number };
  };
}

interface VisibilitySummary {
  share_of_voice?: number;
  total_citations?: number;
  total_runs?: number;
}

interface ActivityItem {
  id: number;
  action: string;
  created_at?: string;
}

export default function DashboardPage() {
  const { token } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [dash, setDash] = useState<DashData | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [visibility, setVisibility] = useState<VisibilitySummary | null>(null);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [bizName, setBizName] = useState("");
  const [bizDesc, setBizDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    loadAll();
  }, [token]);

  async function loadAll() {
    setLoading(true);
    try {
      const [dashRes, usageRes, visRes, actRes] = await Promise.allSettled([
        apiRequest<DashData>("/v1/dashboard", {}, token),
        apiRequest<UsageData>("/v1/usage", {}, token),
        apiRequest<VisibilitySummary>("/v1/visibility/summary", {}, token),
        apiRequest<{ items: ActivityItem[] }>("/v1/activity", {}, token),
      ]);

      if (dashRes.status === "fulfilled") setDash(dashRes.value);
      if (usageRes.status === "fulfilled") setUsage(usageRes.value);
      if (visRes.status === "fulfilled") setVisibility(visRes.value);
      if (actRes.status === "fulfilled") setActivity(actRes.value.items || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function handleCreate() {
    if (!bizName.trim()) {
      toast.warning("Please enter a business name.");
      return;
    }
    setCreating(true);
    try {
      await apiRequest("/v1/projects", {
        method: "POST",
        body: JSON.stringify({
          name: bizName.trim(),
          description: bizDesc.trim() || null,
        }),
      }, token);
      toast.success("Project created!", "Now set up your brand profile.");
      setBizName("");
      setBizDesc("");
      setShowCreate(false);
      loadAll();
    } catch (e: any) {
      toast.error("Could not create project", e.message);
    }
    setCreating(false);
  }

  const hasProject = (dash?.projects?.length || 0) > 0;
  const topOpps = dash?.top_opportunities || [];

  // Setup steps
  const setupStatus = dash?.setup_status;
  const steps = [
    { label: "Create Project", done: hasProject },
    { label: "Set Up Brand", done: setupStatus?.brand_configured || false },
    { label: "Add Audience", done: (setupStatus?.personas_count || 0) > 0 },
    { label: "First Scan", done: topOpps.length > 0 },
    { label: "Track AI Visibility", done: (visibility?.total_runs || 0) > 0 },
  ];
  const currentStep = steps.findIndex((s) => !s.done);
  const completedCount = steps.filter((s) => s.done).length;

  if (loading) {
    return (
      <div>
        <h2 className="page-title">Dashboard</h2>
        <div className="data-grid" style={{ marginTop: 24, gap: 24 }}>
          {[1, 2, 3, 4].map((i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
        <h2 className="page-title">Dashboard</h2>
        {hasProject && <Button onClick={() => setShowCreate(true)}>+ New Project</Button>}
      </div>

      {/* Setup Progress */}
      {completedCount < 5 && (
        <div className="card" style={{ marginBottom: 32, padding: 24 }}>
          <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
            <div>
              <h3 className="card-title">Getting Started</h3>
              <p className="text-muted">
                {completedCount} of {steps.length} steps complete
              </p>
            </div>
            <span
              style={{
                fontSize: 24,
                fontWeight: 700,
                color: "var(--accent)",
              }}
            >
              {Math.round((completedCount / steps.length) * 100)}%
            </span>
          </div>
          <StepIndicator steps={steps} currentStep={currentStep >= 0 ? currentStep : steps.length - 1} />
          <div style={{ marginTop: 16 }}>
            {currentStep === 0 && !hasProject && (
              <Button onClick={() => setShowCreate(true)}>Create Your First Project</Button>
            )}
            {currentStep === 1 && (
              <a href="/app/brand" className="primary-button" style={{ textDecoration: "none" }}>
                Set Up Brand
              </a>
            )}
            {currentStep === 2 && (
              <a href="/app/persona" className="primary-button" style={{ textDecoration: "none" }}>
                Add Audience
              </a>
            )}
            {currentStep === 3 && (
              <a href="/app/discovery" className="primary-button" style={{ textDecoration: "none" }}>
                Run First Scan
              </a>
            )}
            {currentStep === 4 && (
              <a href="/app/visibility" className="primary-button" style={{ textDecoration: "none" }}>
                Track AI Visibility
              </a>
            )}
          </div>
        </div>
      )}

      {/* KPI Cards */}
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", marginBottom: 32, gap: 24 }}>
        <KpiCard
          label="AI Visibility"
          value={`${visibility?.share_of_voice || 0}%`}
          onClick={() => (window.location.href = "/app/visibility")}
        />
        <KpiCard
          label="Opportunities"
          value={topOpps.length}
          onClick={() => (window.location.href = "/app/discovery")}
        />
        <KpiCard
          label="Citations Found"
          value={visibility?.total_citations || 0}
          onClick={() => (window.location.href = "/app/sources")}
        />
        <KpiCard
          label="Prompt Runs"
          value={visibility?.total_runs || 0}
          onClick={() => (window.location.href = "/app/visibility")}
        />
      </div>

      {/* Main Content: Two columns */}
      <div className="data-grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 24 }}>
        {/* Top Opportunities */}
        <div className="card" style={{ padding: 24 }}>
          <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
            <h3 className="card-title">Top Opportunities</h3>
            <a href="/app/discovery" className="ghost-button" style={{ fontSize: 13, textDecoration: "none" }}>
              View all →
            </a>
          </div>
          {topOpps.length === 0 ? (
            <EmptyState icon="🔍" title="No opportunities yet" description="Run a scan to discover matching Reddit threads." />
          ) : (
            <div className="item-list">
              {topOpps.slice(0, 6).map((opp: any) => (
                <div key={opp.id} className="list-row" style={{ padding: "12px 0" }}>
                  <div className="flex justify-between items-center">
                    <div style={{ flex: 1 }}>
                      <div className="flex items-center gap-sm">
                        <PlatformIcon platform="reddit" />
                        <a
                          href={opp.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontWeight: 600,
                            fontSize: 13,
                            color: "var(--ink)",
                            textDecoration: "none",
                          }}
                        >
                          {(opp.title || "").substring(0, 60)}
                          {(opp.title || "").length > 60 ? "..." : ""}
                        </a>
                      </div>
                      <span className="text-muted" style={{ fontSize: 12 }}>
                        r/{opp.subreddit_name}
                      </span>
                    </div>
                    <ScoreBadge score={opp.score || 0} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Activity + Usage */}
        <div>
          {/* Usage */}
          {usage && (
            <div className="card" style={{ marginBottom: 24, padding: 24 }}>
              <h3 className="card-title" style={{ marginBottom: 16 }}>
                Plan Usage
              </h3>
              <UsageMeter
                label="Projects"
                used={usage.metrics?.projects?.used || 0}
                limit={usage.metrics?.projects?.limit || 5}
              />
              <div style={{ marginTop: 12 }}>
                <UsageMeter
                  label="Keywords"
                  used={usage.metrics?.keywords?.used || 0}
                  limit={usage.metrics?.keywords?.limit || 10}
                />
              </div>
              <div style={{ marginTop: 12 }}>
                <UsageMeter
                  label="Communities"
                  used={usage.metrics?.subreddits?.used || 0}
                  limit={usage.metrics?.subreddits?.limit || 5}
                />
              </div>
              <a
                href="/app/subscription"
                className="ghost-button"
                style={{
                  display: "block",
                  textAlign: "center",
                  marginTop: 16,
                  fontSize: 13,
                  textDecoration: "none",
                }}
              >
                {usage.plan === "free" ? "Upgrade Plan →" : "Manage Billing →"}
              </a>
            </div>
          )}

          {/* Activity Timeline */}
          <div className="card" style={{ padding: 24 }}>
            <h3 className="card-title" style={{ marginBottom: 16 }}>
              Recent Activity
            </h3>
            {activity.length === 0 ? (
              <p className="text-muted" style={{ textAlign: "center", padding: 16 }}>
                No activity yet. Start by setting up your brand.
              </p>
            ) : (
              <div className="item-list">
                {activity.slice(0, 8).map((a) => (
                  <div key={a.id} className="list-row" style={{ padding: "8px 0" }}>
                    <div className="text-muted" style={{ fontSize: 13 }}>
                      {a.action.replace(/_/g, " ").replace(/\./g, " → ")}
                    </div>
                    <div className="text-muted" style={{ fontSize: 11 }}>
                      {a.created_at ? new Date(a.created_at).toLocaleDateString() : ""}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Project Form */}
      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Create New Project</h3>
              <button className="ghost-button modal-close" onClick={() => setShowCreate(false)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="field">
                <label className="field-label">Business Name</label>
                <input
                  type="text"
                  value={bizName}
                  onChange={(e) => setBizName(e.target.value)}
                  placeholder="Your company or product name"
                />
              </div>
              <div className="field">
                <label className="field-label">Description (optional)</label>
                <textarea
                  rows={3}
                  value={bizDesc}
                  onChange={(e) => setBizDesc(e.target.value)}
                  placeholder="What does your business do?"
                />
              </div>
            </div>
            <div className="modal-footer">
              <div className="flex gap-md" style={{ justifyContent: "flex-end" }}>
                <button className="secondary-button" onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
                <Button loading={creating} onClick={handleCreate}>
                  Create Project
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
