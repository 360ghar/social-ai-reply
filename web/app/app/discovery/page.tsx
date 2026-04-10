"use client";

import { useEffect, useState, useRef } from "react";
import {
  Loader2,
  Target,
  Users,
  MessageSquare,
  Plus,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Search,
} from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PageHeader } from "@/components/shared/page-header";
import { KPIGrid } from "@/components/shared/kpi-card";
import { EmptyState } from "@/components/shared/empty-state";
import { SheetPanel } from "@/components/shared/sheet-panel";
import { ScoreBadge } from "@/components/shared/score-badge";
import { PlatformIcon } from "@/components/shared/platform-icon";
import { redditUrl, copyText } from "@/lib/reddit";

interface Keyword {
  id: number;
  keyword: string;
  rationale?: string;
  priority_score?: number;
}

interface Subreddit {
  id: number;
  name: string;
  fit_score?: number;
  activity_score?: number;
  description?: string;
}

interface Opportunity {
  id: number;
  title: string;
  subreddit_name: string;
  permalink: string;
  body_excerpt?: string;
  score: number;
  status?: string;
  score_reasons?: string[];
}

interface ReplyDraft {
  content: string;
  rationale?: string;
}

interface ProjectContext {
  id: number;
  name: string;
}

interface Campaign {
  id: number;
  name: string;
  description?: string;
  status?: string;
}

export default function DiscoveryPage() {
  const { token } = useAuth();
  const { success, error, warning } = useToast();
  const selectedProjectId = useSelectedProjectId();

  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<Subreddit[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  const [newKeyword, setNewKeyword] = useState("");
  const [addingKeyword, setAddingKeyword] = useState(false);
  const [generatingKeywords, setGeneratingKeywords] = useState(false);
  const [discoveringCommunities, setDiscoveringCommunities] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [generatingReply, setGeneratingReply] = useState<number | null>(null);

  const [draftingOpp, setDraftingOpp] = useState<Opportunity | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [draftRationale, setDraftRationale] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<{ type: string; id: number; name: string } | null>(null);

  const [statusFilter, setStatusFilter] = useState("");
  const [project, setProject] = useState<ProjectContext | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignFilter, setCampaignFilter] = useState("");
  const [showCampaignModal, setShowCampaignModal] = useState(false);
  const [newCampaignName, setNewCampaignName] = useState("");
  const [newCampaignDesc, setNewCampaignDesc] = useState("");
  const [creatingCampaign, setCreatingCampaign] = useState(false);

  // Collapsible sections in draft panel
  const [showOriginalThread, setShowOriginalThread] = useState(true);
  const [showRationale, setShowRationale] = useState(false);

  // Section refs for workflow strip scroll
  const signalsRef = useRef<HTMLDivElement>(null);
  const communitiesRef = useRef<HTMLDivElement>(null);
  const queueRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadAll();
  }, [token, selectedProjectId]);

  async function loadAll() {
    setLoading(true);
    try {
      const dashRes = await apiRequest<any>(withProjectId("/v1/dashboard", selectedProjectId), {}, token);
      const currentProject =
        dashRes.projects?.find((item: ProjectContext) => item.id === selectedProjectId) ??
        (dashRes.projects && dashRes.projects.length > 0 ? dashRes.projects[0] : null);

      if (!currentProject) {
        setProject(null);
        setLoading(false);
        return;
      }

      setProject(currentProject);

      const projectId = currentProject.id;
      const [kwRes, subRes, oppRes, campRes] = await Promise.allSettled([
        apiRequest<Keyword[]>(`/v1/discovery/keywords?project_id=${projectId}`, {}, token),
        apiRequest<Subreddit[]>(`/v1/discovery/subreddits?project_id=${projectId}`, {}, token),
        apiRequest<Opportunity[]>(`/v1/opportunities?project_id=${projectId}`, {}, token),
        apiRequest<Campaign[]>(`/v1/campaigns?project_id=${projectId}`, {}, token),
      ]);

      if (kwRes.status === "fulfilled") {
        setKeywords(kwRes.value || []);
      }
      if (subRes.status === "fulfilled") {
        setSubreddits(subRes.value || []);
      }
      if (oppRes.status === "fulfilled") {
        setOpportunities(oppRes.value || []);
      }
      if (campRes.status === "fulfilled") {
        setCampaigns(campRes.value || []);
      }
    } catch (err: any) {
      error("Failed to load data", err?.message);
    }
    setLoading(false);
  }

  async function addKeyword() {
    if (!newKeyword.trim() || !project) {
      return;
    }
    setAddingKeyword(true);
    try {
      await apiRequest(
        `/v1/discovery/keywords?project_id=${project.id}`,
        {
          method: "POST",
          body: JSON.stringify({
            keyword: newKeyword.trim(),
            rationale: "Manual",
            priority_score: 5,
            is_active: true,
          }),
        },
        token
      );
      setNewKeyword("");
      success("Signal added");
      await loadAll();
    } catch (err: any) {
      error("Failed to add keyword", err.message);
    }
    setAddingKeyword(false);
  }

  async function generateKeywords() {
    if (!project) {
      return;
    }
    setGeneratingKeywords(true);
    try {
      await apiRequest(
        `/v1/discovery/keywords/generate?project_id=${project.id}`,
        {
          method: "POST",
          body: JSON.stringify({ count: 12 }),
        },
        token
      );
      success("Audience signals generated");
      await loadAll();
    } catch (err: any) {
      error("Failed to generate", err.message);
    }
    setGeneratingKeywords(false);
  }

  async function discoverCommunities() {
    if (!project) {
      return;
    }
    setDiscoveringCommunities(true);
    try {
      await apiRequest(
        `/v1/discovery/subreddits/discover?project_id=${project.id}`,
        {
          method: "POST",
          body: JSON.stringify({ max_subreddits: 8 }),
        },
        token
      );
      success("Communities discovered");
      await loadAll();
    } catch (err: any) {
      error("Failed to discover", err.message);
    }
    setDiscoveringCommunities(false);
  }

  async function runScan() {
    if (!project) {
      return;
    }
    setScanning(true);
    try {
      await apiRequest(
        "/v1/scans",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: project.id,
            search_window_hours: 72,
            max_posts_per_subreddit: 10,
          }),
        },
        token
      );
      success("Scan complete", "Check the conversation queue below.");
      await loadAll();
    } catch (err: any) {
      error("Scan failed", err.message);
    }
    setScanning(false);
  }

  async function generateReply(oppId: number) {
    setGeneratingReply(oppId);
    try {
      const res = await apiRequest<ReplyDraft>(
        "/v1/drafts/replies",
        {
          method: "POST",
          body: JSON.stringify({ opportunity_id: oppId }),
        },
        token
      );
      setDraftContent(res.content || "");
      setDraftRationale(res.rationale || "");
      setDraftingOpp(opportunities.find((opp) => opp.id === oppId) || null);
      setShowOriginalThread(true);
      setShowRationale(false);
      success("Response drafted");
    } catch (err: any) {
      error("Could not generate response", err.message);
    }
    setGeneratingReply(null);
  }

  async function deleteItem() {
    if (!deleteTarget) {
      return;
    }
    try {
      await apiRequest(`/v1/discovery/${deleteTarget.type}/${deleteTarget.id}`, { method: "DELETE" }, token);
      success(`${deleteTarget.name} deleted`);
      setDeleteTarget(null);
      await loadAll();
    } catch (err: any) {
      error("Delete failed", err.message);
    }
  }

  async function copyToClipboard(text: string) {
    try {
      await copyText(text);
      success("Copied to clipboard");
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
    }
  }

  async function copyAndOpenReddit(text: string, permalink: string) {
    try {
      await copyText(text);
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
      return;
    }
    window.open(redditUrl(permalink), "_blank");
    success("Draft copied. Reddit is opening so you can review and paste.");
  }

  async function markAsPosted(oppId: number) {
    try {
      await apiRequest(
        `/v1/opportunities/${oppId}/status`,
        {
          method: "PUT",
          body: JSON.stringify({ status: "posted" }),
        },
        token
      );
      success("Marked as posted");
      setDraftingOpp(null);
      await loadAll();
    } catch (err: any) {
      error("Could not update status", err.message);
    }
  }

  async function createCampaign() {
    if (!project || !newCampaignName.trim()) {
      warning("Please enter a campaign name");
      return;
    }
    setCreatingCampaign(true);
    try {
      const campaign = await apiRequest<Campaign>(
        "/v1/campaigns",
        {
          method: "POST",
          body: JSON.stringify({
            project_id: project.id,
            name: newCampaignName.trim(),
            description: newCampaignDesc.trim() || null,
          }),
        },
        token
      );
      setCampaigns((prev) => [campaign, ...prev]);
      setNewCampaignName("");
      setNewCampaignDesc("");
      setShowCampaignModal(false);
      success("Campaign created");
    } catch (err: any) {
      error("Failed to create campaign", err.message);
    }
    setCreatingCampaign(false);
  }

  // Workflow step definitions
  const workflowSteps = [
    { label: "Signals", count: keywords.length, done: keywords.length > 0, ref: signalsRef },
    { label: "Communities", count: subreddits.length, done: subreddits.length > 0, ref: communitiesRef },
    { label: "Queue", count: opportunities.length, done: opportunities.length > 0, ref: queueRef },
  ];
  const currentStep = workflowSteps.findIndex((step) => !step.done);

  // Filtered opportunities
  let filteredOpps = [...opportunities];
  if (statusFilter) {
    filteredOpps = filteredOpps.filter((opp) => opp.status === statusFilter);
  }
  filteredOpps.sort((a, b) => (b.score || 0) - (a.score || 0));

  // Status filter tabs
  const statusTabs = [
    { label: "All", value: "" },
    { label: "New", value: "new" },
    { label: "Saved", value: "saved" },
    { label: "Drafting", value: "drafting" },
    { label: "Posted", value: "posted" },
    { label: "Ignored", value: "ignored" },
  ];

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-16 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="text-4xl">PRJ</div>
        <h3 className="mt-4 text-lg font-medium">No project selected</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Go to Command Center first and create a project before building an engagement workflow.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      {/* Page Header */}
      <PageHeader
        title="Opportunity Radar"
        description="Discover live Reddit conversations using a workflow shaped for broader forum, Q&A, and social comment patterns."
        actions={
          <div className="flex items-center gap-2">
            {campaigns.length > 0 && (
              <Button variant="ghost" size="sm" onClick={() => setShowCampaignModal(true)}>
                <Plus className="h-4 w-4" />
                Campaign
              </Button>
            )}
            <Button onClick={runScan} disabled={scanning || subreddits.length === 0}>
              {scanning && <Loader2 className="h-4 w-4 animate-spin" />}
              {scanning ? "Scanning..." : "Run Scan"}
            </Button>
          </div>
        }
      />

      {/* Campaign Chips */}
      {campaigns.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Campaigns:</span>
          {campaigns.map((campaign) => (
            <Badge key={campaign.id} variant="secondary">
              {campaign.name}
              {campaign.status && <span className="text-[11px] opacity-70">({campaign.status})</span>}
            </Badge>
          ))}
        </div>
      )}

      {/* KPI Grid */}
      <KPIGrid
        columns={3}
        cards={[
          { label: "Signals", value: keywords.length, icon: Target },
          { label: "Communities", value: subreddits.length, icon: Users },
          { label: "Queue", value: filteredOpps.length, icon: MessageSquare },
        ]}
      />

      {/* Workflow Strip */}
      <Card>
        <CardContent className="py-3">
          <div className="flex items-center justify-center gap-1">
            {workflowSteps.map((step, i) => (
              <div key={step.label} className="flex items-center">
                <button
                  type="button"
                  onClick={() => step.ref.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
                  className="flex items-center gap-1.5 rounded-md px-3 py-1.5 transition-colors hover:bg-muted"
                >
                  <span
                    className={cn(
                      "flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium transition-colors",
                      step.done
                        ? "bg-primary text-primary-foreground"
                        : i === currentStep
                          ? "bg-primary/10 text-primary ring-2 ring-primary/30"
                          : "bg-muted text-muted-foreground"
                    )}
                  >
                    {step.done ? "\u2713" : i + 1}
                  </span>
                  <span className="text-sm font-medium text-foreground">{step.label}</span>
                  <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
                    {step.count}
                  </Badge>
                </button>
                {i < workflowSteps.length - 1 && (
                  <div
                    className={cn(
                      "h-0.5 w-6",
                      step.done ? "bg-primary" : "bg-muted"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Section 1: Audience Signals */}
      <div ref={signalsRef}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Audience Signals
              <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
                {keywords.length}
              </Badge>
            </CardTitle>
            <CardAction>
              <Button variant="outline" size="sm" onClick={generateKeywords} disabled={generatingKeywords}>
                {generatingKeywords ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Generate Signals
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                type="text"
                value={newKeyword}
                onChange={(event) => setNewKeyword(event.target.value)}
                placeholder="Add a market phrase or audience signal"
                onKeyDown={(event) => event.key === "Enter" && void addKeyword()}
                className="flex-1"
              />
              <Button size="sm" onClick={addKeyword} disabled={addingKeyword}>
                {addingKeyword ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Add
              </Button>
            </div>
            {keywords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {keywords.map((keyword) => (
                  <Badge key={keyword.id} variant="secondary" className="inline-flex items-center gap-1.5">
                    {keyword.keyword}
                    <button
                      onClick={() => setDeleteTarget({ type: "keywords", id: keyword.id, name: keyword.keyword })}
                      className="ml-0.5 text-muted-foreground hover:text-foreground"
                    >
                      x
                    </button>
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Add audience signals or generate them from your project description to seed community discovery.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 2: Community Coverage */}
      <div ref={communitiesRef}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Community Coverage
              <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
                {subreddits.length}
              </Badge>
            </CardTitle>
            <CardAction>
              <Button
                variant="outline"
                size="sm"
                onClick={discoverCommunities}
                disabled={discoveringCommunities || keywords.length === 0}
              >
                {discoveringCommunities ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Discover Communities
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent>
            {subreddits.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No communities yet"
                description="Add audience signals first, then discover communities that match those intents."
              />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {subreddits.map((community) => (
                  <div
                    key={community.id}
                    className="flex items-center justify-between rounded-lg border bg-card p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <PlatformIcon platform="reddit" />
                        <span className="text-sm font-medium truncate">r/{community.name}</span>
                      </div>
                      {community.description && (
                        <p className="mt-1 text-xs text-muted-foreground truncate">
                          {community.description.substring(0, 80)}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-3">
                      {community.fit_score !== undefined && (
                        <ScoreBadge score={community.fit_score} />
                      )}
                      <button
                        onClick={() => setDeleteTarget({ type: "subreddits", id: community.id, name: `r/${community.name}` })}
                        className="text-muted-foreground hover:text-foreground text-xs"
                      >
                        x
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Section 3: Conversation Queue */}
      <div ref={queueRef}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Conversation Queue
              <Badge variant="secondary" className="text-[11px] px-1.5 py-0">
                {filteredOpps.length}
              </Badge>
            </CardTitle>
            <CardAction>
              <div className="flex items-center gap-2">
                {campaigns.length > 0 && (
                  <Select value={campaignFilter} onValueChange={(v) => setCampaignFilter(v ?? "")}>
                    <SelectTrigger className="h-8 w-[140px] text-xs">
                      <SelectValue placeholder="All Campaigns" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">All Campaigns</SelectItem>
                      {campaigns.map((c) => (
                        <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Status Filter Pills */}
            <div className="flex flex-wrap gap-1.5">
              {statusTabs.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => setStatusFilter(tab.value)}
                  className={cn(
                    "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                    statusFilter === tab.value
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Opportunity List */}
            {filteredOpps.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title={opportunities.length === 0 ? "No conversations found yet" : "No matches for this filter"}
                description={
                  opportunities.length === 0
                    ? "Add signals, discover communities, then scan for reply-ready discussions."
                    : "Try changing the status filter."
                }
                action={
                  subreddits.length > 0
                    ? { label: "Run Scan", onClick: () => void runScan() }
                    : undefined
                }
              />
            ) : (
              <div className="space-y-2">
                {filteredOpps.map((opp) => (
                  <div
                    key={opp.id}
                    className="flex flex-col sm:flex-row sm:items-center gap-3 rounded-lg border bg-card p-4"
                  >
                    {/* Left: Platform + subreddit */}
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <Badge variant="outline" className="text-xs">r/{opp.subreddit_name}</Badge>
                    </div>

                    {/* Center: Title + score reasons */}
                    <div className="flex-1 min-w-0">
                      <a
                        href={redditUrl(opp.permalink)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-foreground hover:underline truncate block"
                      >
                        {opp.title}
                      </a>
                      {(opp.score_reasons || []).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {(opp.score_reasons || []).slice(0, 3).map((reason) => (
                            <Badge key={reason} variant="secondary" className="text-[11px] px-1.5 py-0">
                              {reason}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Right: Score + Action */}
                    <div className="flex items-center gap-2 shrink-0">
                      <ScoreBadge score={opp.score || 0} />
                      <Button
                        size="sm"
                        onClick={() => generateReply(opp.id)}
                        disabled={generatingReply === opp.id}
                      >
                        {generatingReply === opp.id && <Loader2 className="h-4 w-4 animate-spin" />}
                        Draft Reply
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Reply Draft Sheet */}
      <SheetPanel
        title="Reply Draft"
        description={draftingOpp?.title?.substring(0, 60) || ""}
        open={!!draftingOpp}
        onOpenChange={(open) => !open && setDraftingOpp(null)}
        width="lg"
        footer={
          <div className="flex flex-wrap gap-2">
            <a href="/app/content">
              <Button variant="ghost" size="sm">Review in Studio</Button>
            </a>
            <Button variant="outline" size="sm" onClick={() => copyToClipboard(draftContent)}>
              Copy
            </Button>
            {draftingOpp?.permalink && (
              <Button size="sm" onClick={() => copyAndOpenReddit(draftContent, draftingOpp.permalink)}>
                Copy &amp; Open Reddit
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => draftingOpp && markAsPosted(draftingOpp.id)}>
              Mark as Posted
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {/* Collapsible: Original Thread */}
          {draftingOpp?.permalink && (
            <div className="rounded-lg border">
              <button
                type="button"
                onClick={() => setShowOriginalThread(!showOriginalThread)}
                className="flex w-full items-center justify-between p-3 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
              >
                <span>Original Thread</span>
                {showOriginalThread ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {showOriginalThread && (
                <div className="border-t px-3 pb-3 pt-2">
                  <a
                    href={redditUrl(draftingOpp.permalink)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                  >
                    View on Reddit <ExternalLink className="h-3 w-3" />
                  </a>
                  {draftingOpp.body_excerpt && (
                    <p className="mt-2 text-xs text-muted-foreground leading-snug">
                      {draftingOpp.body_excerpt.substring(0, 280)}...
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Draft Textarea */}
          <div className="space-y-2">
            <Label>Generated Response</Label>
            <Textarea
              rows={10}
              value={draftContent}
              onChange={(event) => setDraftContent(event.target.value)}
              className="text-sm leading-relaxed"
            />
            <p className="text-xs text-muted-foreground">{draftContent.length} characters</p>
          </div>

          {/* Collapsible: Rationale */}
          {draftRationale && (
            <div className="rounded-lg border">
              <button
                type="button"
                onClick={() => setShowRationale(!showRationale)}
                className="flex w-full items-center justify-between p-3 text-sm font-medium text-foreground hover:bg-muted/50 transition-colors"
              >
                <span>Why this response works</span>
                {showRationale ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {showRationale && (
                <div className="border-t px-3 pb-3 pt-2">
                  <p className="text-sm text-muted-foreground">{draftRationale}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </SheetPanel>

      {/* Delete Confirm */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {deleteTarget?.name || ""}?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. Are you sure?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={deleteItem} variant="destructive">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Create Campaign Dialog */}
      <Dialog open={showCampaignModal} onOpenChange={setShowCampaignModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Campaign</DialogTitle>
            <DialogDescription>Set up a new engagement campaign for your project.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Campaign Name</Label>
              <Input
                type="text"
                value={newCampaignName}
                onChange={(e) => setNewCampaignName(e.target.value)}
                placeholder="e.g., Q4 Engagement"
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                rows={3}
                value={newCampaignDesc}
                onChange={(e) => setNewCampaignDesc(e.target.value)}
                placeholder="What is this campaign focused on?"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCampaignModal(false)}>
              Cancel
            </Button>
            <Button onClick={() => void createCampaign()} disabled={creatingCampaign}>
              {creatingCampaign && <Loader2 className="h-4 w-4 animate-spin" />}
              {creatingCampaign ? "Creating..." : "Create Campaign"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
