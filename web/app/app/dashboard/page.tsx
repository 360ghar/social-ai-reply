"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { apiRequest, type Project } from "@/lib/api";
import { setStoredProjectId, withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";

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

interface WorkflowStep {
  label: string;
  title: string;
  description: string;
  actionLabel: string;
  done: boolean;
  href?: string;
  actionKind: "route" | "modal";
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
  const router = useRouter();
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
  const [autoPipelineUrl, setAutoPipelineUrl] = useState("");
  const [dismissedWizard, setDismissedWizard] = useState(false);

  useEffect(() => {
    if (!token) {
      return;
    }
    const dismissed = localStorage.getItem("wizard-dismissed") === "true";
    setDismissedWizard(dismissed);
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
    } catch (err: any) {
      toast.error("Failed to load dashboard", err?.message);
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
      const createdProject = await apiRequest<Project>(
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
      setStoredProjectId(createdProject.id);
      toast.success("Project created", "Next: add your first audience.");
      setBizName("");
      setBizDesc("");
      setShowCreate(false);
      router.push("/app/persona");
    } catch (error: any) {
      toast.error("Could not create project", error.message);
    }
    setCreating(false);
  }

  function dismissWizard() {
    localStorage.setItem("wizard-dismissed", "true");
    setDismissedWizard(true);
  }

  function handleAutoPipeline() {
    if (!autoPipelineUrl.trim()) {
      toast.warning("Please enter a URL");
      return;
    }
    router.push(`/app/auto-pipeline?url=${encodeURIComponent(autoPipelineUrl)}`);
  }

  const hasProject = (dash?.projects?.length || 0) > 0;
  const focusProject =
    dash?.projects?.find((project) => project.id === selectedProjectId) ??
    dash?.projects?.[0] ??
    null;
  const topOpps = dash?.top_opportunities || [];
  const setupStatus = dash?.setup_status;
  const steps: WorkflowStep[] = [
    {
      label: "Create Project",
      title: "Create your first project",
      description: "Start a project to connect brand setup, audience signals, community mapping, and visibility tracking.",
      actionLabel: "Create Project",
      done: hasProject,
      actionKind: "modal",
    },
    {
      label: "Define Brand",
      title: "Review your brand profile",
      description: "Add your website, product summary, audience, and voice so the rest of the workflow has solid context.",
      actionLabel: "Open Brand",
      done: setupStatus?.brand_configured || false,
      href: "/app/brand",
      actionKind: "route",
    },
    {
      label: "Add Audience",
      title: "Add your first audience",
      description: "Create a customer type so discovery can generate stronger signals and surface more relevant conversations.",
      actionLabel: "Open Audience",
      done: (setupStatus?.personas_count || 0) > 0,
      href: "/app/persona",
      actionKind: "route",
    },
    {
      label: "Map Communities",
      title: "Discover matching communities",
      description: "Turn audience signals into monitored Reddit communities and prepare the engagement queue.",
      actionLabel: "Open Radar",
      done: (setupStatus?.subreddits_count || 0) > 0,
      href: "/app/discovery",
      actionKind: "route",
    },
    {
      label: "Track Visibility",
      title: "Run your first visibility check",
      description: "Create or run a prompt set so the dashboard can start tracking AI share of voice and citations.",
      actionLabel: "Open AI Visibility",
      done: (visibility?.total_runs || 0) > 0,
      href: "/app/visibility",
      actionKind: "route",
    },
  ];
  const currentStep = steps.findIndex((step) => !step.done);
  const completedCount = steps.filter((step) => step.done).length;
  const nextStep = steps.find((step) => !step.done) ?? null;

  if (loading) {
    return (
      <div className="grid gap-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-24 w-full rounded-lg" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      {/* Auto-Pipeline Banner */}
      <div
        className="rounded-xl p-6"
        style={{
          background: "linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
          color: "white",
        }}
      >
        <div className="mb-4">
          <h3 className="mb-2 text-base font-semibold text-white">Launch Auto-Pipeline</h3>
          <p className="text-sm leading-relaxed" style={{ color: "rgba(255, 255, 255, 0.9)" }}>
            Enter any website URL and get a complete engagement strategy in minutes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            type="url"
            value={autoPipelineUrl}
            onChange={(e) => setAutoPipelineUrl(e.target.value)}
            placeholder="https://example.com"
            className="h-8 flex-1 border-none text-sm"
            onKeyDown={(e) => e.key === "Enter" && handleAutoPipeline()}
          />
          <Button
            onClick={handleAutoPipeline}
            className="bg-white font-semibold text-indigo-500 hover:bg-white/90"
          >
            Go
          </Button>
        </div>
      </div>

      {/* Hero Card */}
      <Card className="p-6">
        <div className="mb-6 flex items-start justify-between border-b pb-6">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Product Overview
            </div>
            <h2 className="mb-2.5 text-lg font-semibold text-foreground">
              Build a complete visibility-to-engagement workflow
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              The platform already does two things well: AI visibility tracking and guided community
              engagement. The next step is making those two motions feel like one coordinated system.
            </p>
          </div>
          <Button onClick={() => setShowCreate(true)}>New Project</Button>
        </div>

        {focusProject ? (
          !dismissedWizard ? (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {/* Focus Project Card */}
              <Card className="p-5">
                <Badge className="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                  Focused Project
                </Badge>
                <h3 className="mt-3 mb-2.5 text-base font-semibold text-foreground">
                  {focusProject.name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {focusProject.description ||
                    "Use this project as the active scope for communities, drafts, prompt sets, and source analysis."}
                </p>
              </Card>

              {/* Workflow Status Card */}
              <Card className="p-5">
                <Badge variant="outline">Workflow Status</Badge>

                {/* Step Indicator */}
                <div className="mt-3.5 flex items-center gap-1">
                  {steps.map((step, idx) => (
                    <div key={step.label} className="flex items-center gap-1">
                      <div
                        className={`h-2 flex-1 rounded-full transition-colors ${
                          step.done
                            ? "bg-primary"
                            : idx === currentStep
                              ? "bg-primary/40"
                              : "bg-muted"
                        }`}
                        style={{ minWidth: 28 }}
                      />
                    </div>
                  ))}
                </div>

                <p className="mt-3.5 text-sm text-muted-foreground">
                  {completedCount} of {steps.length} foundations are in place.
                </p>

                <div className="mt-4 rounded-2xl border bg-muted/50 p-4">
                  <div className="grid gap-2.5">
                    <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {nextStep ? "Next Step" : "Workflow Ready"}
                    </div>
                    <h3 className="text-sm font-semibold text-foreground">
                      {nextStep ? nextStep.title : "All setup steps are complete"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {nextStep
                        ? nextStep.description
                        : "Your setup foundations are in place. Move into visibility tracking or engagement workflows next."}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      {nextStep ? (
                        nextStep.actionKind === "modal" ? (
                          <Button onClick={() => setShowCreate(true)}>{nextStep.actionLabel}</Button>
                        ) : (
                          <Button onClick={() => nextStep.href && router.push(nextStep.href)}>
                            {nextStep.actionLabel}
                          </Button>
                        )
                      ) : (
                        <>
                          <Button onClick={() => router.push("/app/visibility")}>
                            Open AI Visibility
                          </Button>
                          <Button variant="outline" onClick={() => router.push("/app/discovery")}>
                            Open Radar
                          </Button>
                        </>
                      )}
                    </div>
                    {completedCount === steps.length && (
                      <Button
                        variant="ghost"
                        onClick={dismissWizard}
                        className="mt-2 justify-start text-muted-foreground"
                      >
                        Dismiss setup wizard
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            </div>
          ) : (
            <div className="p-6 text-center text-sm text-muted-foreground">
              <p>{focusProject.name} &bull; Ready for engagement workflows</p>
            </div>
          )
        ) : (
          /* Empty State - No Projects */
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <span className="mb-4 text-4xl">📋</span>
            <h3 className="mb-1 text-sm font-semibold text-foreground">No projects yet</h3>
            <p className="mb-4 text-xs text-muted-foreground">
              Create a project to connect brand setup, AI visibility, communities, and draft
              generation.
            </p>
            <Button onClick={() => setShowCreate(true)}>Create Your First Project</Button>
          </div>
        )}
      </Card>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">{visibility?.share_of_voice || 0}%</div>
          <div className="text-xs text-muted-foreground">Visibility Score</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">{topOpps.length}</div>
          <div className="text-xs text-muted-foreground">Opportunities</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">0</div>
          <div className="text-xs text-muted-foreground">Drafts Ready</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-foreground">0</div>
          <div className="text-xs text-muted-foreground">Published</div>
        </Card>
      </div>

      {/* Lane Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {LANE_COPY.map((lane) => (
          <Card key={lane.title} className="p-5">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {lane.title}
            </div>
            <p className="mb-5 mt-2 text-sm text-muted-foreground">{lane.body}</p>
            <Button variant="outline" className="w-full">
              <a href={lane.href}>{lane.action}</a>
            </Button>
          </Card>
        ))}
      </div>

      {/* Main Content: Priority Queue + Sidebar */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        {/* Priority Queue */}
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Priority Queue</CardTitle>
              <CardDescription>
                High-fit conversations surfaced from the current community workflow. Reddit is live
                today, but the queue is being shaped for broader Q&A and social patterns.
              </CardDescription>
            </div>
            <Button variant="ghost" className="w-full">
              <a href="/app/discovery">Open Radar</a>
            </Button>
          </CardHeader>

          {topOpps.length === 0 ? (
            <CardContent>
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <span className="mb-4 text-4xl">Q</span>
                <h3 className="mb-1 text-sm font-semibold text-foreground">No opportunities yet</h3>
                <p className="text-xs text-muted-foreground">
                  Run your first community scan after adding audience signals and monitored
                  communities.
                </p>
              </div>
            </CardContent>
          ) : (
            <CardContent>
              <div className="space-y-3">
                {topOpps.slice(0, 6).map((opp: any) => (
                  <div
                    key={opp.id}
                    className="rounded-lg border bg-card p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex h-4 w-4 items-center justify-center rounded text-xs font-bold text-orange-500">
                            R
                          </span>
                          <Badge variant="outline">Live Source</Badge>
                          <span className="text-xs text-muted-foreground">Reply opportunity</span>
                        </div>
                        <a
                          href={opp.permalink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2.5 inline-block text-sm font-semibold text-foreground hover:underline"
                        >
                          {opp.title}
                        </a>
                      </div>
                      {/* Score Badge */}
                      <Badge
                        variant="outline"
                        className={
                          (opp.score || 0) >= 70
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                            : (opp.score || 0) >= 40
                              ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                              : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        }
                      >
                        {opp.score || 0}
                      </Badge>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Badge variant="secondary">r/{opp.subreddit_name}</Badge>
                      {(opp.score_reasons || []).slice(0, 2).map((reason: string) => (
                        <Badge key={reason} variant="secondary">
                          {reason}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Sidebar */}
        <div className="grid gap-6">
          {/* Usage Section */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Project Footprint</CardTitle>
                <CardDescription>
                  Current selected project usage inside the unlocked workspace.
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { label: "Projects", used: usage?.metrics?.projects?.used || 0, limit: usage?.metrics?.projects?.limit || 1 },
                  { label: "Keywords", used: usage?.metrics?.keywords?.used || 0, limit: usage?.metrics?.keywords?.limit || 10 },
                  { label: "Communities", used: usage?.metrics?.subreddits?.used || 0, limit: usage?.metrics?.subreddits?.limit || 5 },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{item.label}</span>
                    <span className="tabular-nums">{item.used}/{item.limit}</span>
                    <Progress value={(item.used / item.limit) * 100} className="flex-1 mx-3" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Activity Section */}
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Recent Activity</CardTitle>
                <CardDescription>Workspace actions and system events.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {activity.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No activity yet. Start with brand setup or a visibility run.
                </p>
              ) : (
                <div className="space-y-3">
                  {activity.slice(0, 6).map((item) => (
                    <div key={item.id} className="flex items-center gap-1.5 rounded-lg border bg-card p-4">
                      <strong className="text-sm font-medium text-foreground">
                        {item.action.replace(/_/g, " ").replace(/\./g, " -> ")}
                      </strong>
                      <span className="text-xs text-muted-foreground">
                        {item.created_at ? new Date(item.created_at).toLocaleString() : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Create Project Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="biz-name">Business Name</Label>
              <Input
                id="biz-name"
                type="text"
                value={bizName}
                onChange={(e) => setBizName(e.target.value)}
                placeholder="Your company or product name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="biz-desc">Description</Label>
              <Textarea
                id="biz-desc"
                rows={3}
                value={bizDesc}
                onChange={(e) => setBizDesc(e.target.value)}
                placeholder="What category, workflow, or audience does this project represent?"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
