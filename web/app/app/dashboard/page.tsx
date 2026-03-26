"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import {
  Button,
  EmptyState,
  KpiCard,
  SkeletonCard,
  StepIndicator,
  UsageMeter,
  ScoreBadge,
  PlatformIcon,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/lib/use-selected-project";

interface SetupStatus {
  brand_configured: boolean;
  personas_count: number;
  subreddits_count: number;
}

interface DashData {
  projects: {
    id: number;
    name: string;
    description?: string | null;
  }[];
  top_opportunities: any[];
  subscription: any;
  setup_status?: SetupStatus;
}

interface UsageData {
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
  brand_mentioned?: number;
}

interface ActivityItem {
  id: number;
  action: string;
  created_at?: string;
}

const LANE_COPY = [
  {
    title: "Visibility Lane",
    body: "Track how AI models recommend your brand, which domains they cite, and where competitors outrank you.",
    href: "/app/visibility",
    action: "Run Prompt Set",
  },
  {
    title: "Community Lane",
    body: "Convert audience signals into monitored communities and review reply-ready conversations with fit and risk context.",
    href: "/app/discovery",
    action: "Open Radar",
  },
  {
    title: "Publishing Lane",
    body: "Turn community insights into reply drafts or original posts, then review and publish manually with control.",
    href: "/app/content",
    action: "Open Studio",
  },
];

export default function DashboardPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
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
    if (!token) {
      return;
    }
    void loadAll();
  }, [token, selectedProjectId]);

  async function loadAll() {
    setLoading(true);
    try {
      const [dashRes, usageRes, visRes, actRes] = await Promise.allSettled([
        apiRequest<DashData>(withProjectId("/v1/dashboard", selectedProjectId), {}, token),
        apiRequest<UsageData>(withProjectId("/v1/usage", selectedProjectId), {}, token),
        apiRequest<VisibilitySummary>(withProjectId("/v1/visibility/summary", selectedProjectId), {}, token),
        apiRequest<{ items: ActivityItem[] }>("/v1/activity", {}, token),
      ]);

      if (dashRes.status === "fulfilled") {
        setDash(dashRes.value);
      }
      if (usageRes.status === "fulfilled") {
        setUsage(usageRes.value);
      }
      if (visRes.status === "fulfilled") {
        setVisibility(visRes.value);
      }
      if (actRes.status === "fulfilled") {
        setActivity(actRes.value.items || []);
      }
    } catch (error) {
      console.error(error);
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
      await apiRequest(
        "/v1/projects",
        {
          method: "POST",
          body: JSON.stringify({
            name: bizName.trim(),
            description: bizDesc.trim() || null,
          }),
        },
        token
      );
      toast.success("Project created", "Set up your brand profile next.");
      setBizName("");
      setBizDesc("");
      setShowCreate(false);
      await loadAll();
    } catch (error: any) {
      toast.error("Could not create project", error.message);
    }
    setCreating(false);
  }

  const hasProject = (dash?.projects?.length || 0) > 0;
  const focusProject =
    dash?.projects?.find((project) => project.id === selectedProjectId) ??
    dash?.projects?.[0] ??
    null;
  const topOpps = dash?.top_opportunities || [];
  const setupStatus = dash?.setup_status;
  const steps = [
    { label: "Create Project", done: hasProject },
    { label: "Define Brand", done: setupStatus?.brand_configured || false },
    { label: "Add Audience", done: (setupStatus?.personas_count || 0) > 0 },
    { label: "Map Communities", done: (setupStatus?.subreddits_count || 0) > 0 },
    { label: "Track Visibility", done: (visibility?.total_runs || 0) > 0 },
  ];
  const currentStep = steps.findIndex((step) => !step.done);
  const completedCount = steps.filter((step) => step.done).length;

  if (loading) {
    return (
      <div>
        <div className="section-grid" style={{ marginBottom: 24 }}>
          {[1, 2, 3].map((item) => (
            <SkeletonCard key={item} />
          ))}
        </div>
        <div className="data-grid" style={{ gap: 24 }}>
          {[1, 2, 3, 4].map((item) => (
            <SkeletonCard key={item} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <section className="card dashboard-hero-card">
        <div className="dashboard-hero-head">
          <div>
            <div className="eyebrow">Product Overview</div>
            <h2 style={{ marginBottom: 10 }}>Build a complete visibility-to-engagement workflow</h2>
            <p className="kicker">
              The platform already does two things well: AI visibility tracking and guided community engagement.
              The next step is making those two motions feel like one coordinated system.
            </p>
          </div>
          <Button onClick={() => setShowCreate(true)}>New Project</Button>
        </div>

        {focusProject ? (
          <div className="dashboard-focus-grid">
            <div className="dashboard-focus-card">
              <span className="badge badge-info">Focused Project</span>
              <h3 style={{ marginTop: 12, marginBottom: 10 }}>{focusProject.name}</h3>
              <p>
                {focusProject.description || "Use this project as the active scope for communities, drafts, prompt sets, and source analysis."}
              </p>
            </div>
            <div className="dashboard-focus-card">
              <span className="badge">Workflow Status</span>
              <div style={{ marginTop: 14 }}>
                <StepIndicator
                  steps={steps}
                  currentStep={currentStep >= 0 ? currentStep : steps.length - 1}
                />
              </div>
              <p style={{ marginTop: 14 }}>
                {completedCount} of {steps.length} foundations are in place.
              </p>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No projects yet"
            description="Create a project to connect brand setup, AI visibility, communities, and draft generation."
            action={<Button onClick={() => setShowCreate(true)}>Create Your First Project</Button>}
          />
        )}
      </section>

      <div className="data-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
        <KpiCard label="Share of Voice" value={`${visibility?.share_of_voice || 0}%`} />
        <KpiCard label="Prompt Runs" value={visibility?.total_runs || 0} />
        <KpiCard label="Citations Found" value={visibility?.total_citations || 0} />
        <KpiCard label="Reply Opportunities" value={topOpps.length} />
      </div>

      <div className="section-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        {LANE_COPY.map((lane) => (
          <div key={lane.title} className="card dashboard-lane-card">
            <div className="eyebrow">{lane.title}</div>
            <p style={{ marginBottom: 20 }}>{lane.body}</p>
            <a href={lane.href} className="secondary-button" style={{ width: "100%", textDecoration: "none" }}>
              {lane.action}
            </a>
          </div>
        ))}
      </div>

      <div className="layout-two">
        <section className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Priority Queue</h3>
              <p className="card-description">
                High-fit conversations surfaced from the current community workflow. Reddit is live today, but the queue is being shaped for broader Q&A and social patterns.
              </p>
            </div>
            <a href="/app/discovery" className="ghost-button" style={{ textDecoration: "none" }}>
              Open Radar
            </a>
          </div>

          {topOpps.length === 0 ? (
            <EmptyState
              icon="Q"
              title="No opportunities yet"
              description="Run your first community scan after adding audience signals and monitored communities."
            />
          ) : (
            <div className="item-list">
              {topOpps.slice(0, 6).map((opp: any) => (
                <div key={opp.id} className="list-row dashboard-opp-row">
                  <div className="dashboard-opp-head">
                    <div>
                      <div className="flex items-center gap-sm">
                        <PlatformIcon platform="reddit" />
                        <span className="badge">Live Source</span>
                        <span className="text-muted text-sm">Reply opportunity</span>
                      </div>
                      <a
                        href={opp.permalink}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: "inline-block", fontWeight: 600, marginTop: 10 }}
                      >
                        {opp.title}
                      </a>
                    </div>
                    <ScoreBadge score={opp.score || 0} />
                  </div>
                  <div className="badge-row">
                    <span className="badge">r/{opp.subreddit_name}</span>
                    {(opp.score_reasons || []).slice(0, 2).map((reason: string) => (
                      <span key={reason} className="badge">
                        {reason}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <div style={{ display: "grid", gap: 24 }}>
          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Project Footprint</h3>
                <p className="card-description">Current selected project usage inside the unlocked workspace.</p>
              </div>
            </div>
            <div style={{ display: "grid", gap: 14 }}>
              <UsageMeter
                label="Projects"
                used={usage?.metrics?.projects?.used || 0}
                limit={usage?.metrics?.projects?.limit || 1}
              />
              <UsageMeter
                label="Keywords"
                used={usage?.metrics?.keywords?.used || 0}
                limit={usage?.metrics?.keywords?.limit || 10}
              />
              <UsageMeter
                label="Communities"
                used={usage?.metrics?.subreddits?.used || 0}
                limit={usage?.metrics?.subreddits?.limit || 5}
              />
            </div>
          </section>

          <section className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Recent Activity</h3>
                <p className="card-description">Workspace actions and system events.</p>
              </div>
            </div>
            {activity.length === 0 ? (
              <p className="text-muted">No activity yet. Start with brand setup or a visibility run.</p>
            ) : (
              <div className="item-list">
                {activity.slice(0, 6).map((item) => (
                  <div key={item.id} className="list-row" style={{ gap: 6 }}>
                    <strong style={{ fontSize: 14 }}>
                      {item.action.replace(/_/g, " ").replace(/\./g, " -> ")}
                    </strong>
                    <span className="text-muted text-sm">
                      {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Create New Project</h3>
              <button className="ghost-button modal-close" onClick={() => setShowCreate(false)}>
                x
              </button>
            </div>
            <div className="modal-body">
              <div className="field">
                <label className="field-label">Business Name</label>
                <input
                  type="text"
                  value={bizName}
                  onChange={(event) => setBizName(event.target.value)}
                  placeholder="Your company or product name"
                />
              </div>
              <div className="field">
                <label className="field-label">Description</label>
                <textarea
                  rows={3}
                  value={bizDesc}
                  onChange={(event) => setBizDesc(event.target.value)}
                  placeholder="What category, workflow, or audience does this project represent?"
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
