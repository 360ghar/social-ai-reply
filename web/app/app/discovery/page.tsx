"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
  SheetDescription,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
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

  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);
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
      setSelectedOpp(opportunities.find((opp) => opp.id === oppId) || null);
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
      setSelectedOpp(null);
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

  const steps = [
    { label: "Audience Signals", done: keywords.length > 0 },
    { label: "Community Coverage", done: subreddits.length > 0 },
    { label: "Conversation Queue", done: opportunities.length > 0 },
  ];
  const currentStep = steps.findIndex((step) => !step.done);

  let filteredOpps = [...opportunities];
  if (statusFilter) {
    filteredOpps = filteredOpps.filter((opp) => opp.status === statusFilter);
  }
  filteredOpps.sort((a, b) => (b.score || 0) - (a.score || 0));

  if (loading) {
    return (
      <div className="flex items-center justify-center p-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Engagement Workflow</p>
        <h2 className="text-2xl font-semibold tracking-tight">Engagement Radar</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Discover live Reddit conversations now using a workflow shaped for broader forum, Q and A, and social comment patterns over time.
        </p>
      </div>

      {campaigns.length > 0 && (
        <Card>
          <CardContent>
            <div className="flex items-center justify-between mb-3">
              <Label className="text-sm font-medium">Active Campaigns</Label>
              <Button
                variant="ghost"
                size="xs"
                onClick={() => setShowCampaignModal(true)}
              >
                + New Campaign
              </Button>
            </div>
            <div className="flex flex-wrap gap-2">
              {campaigns.map((campaign) => (
                <Badge key={campaign.id} variant="secondary">
                  {campaign.name}
                  {campaign.status && <span className="text-[11px] opacity-70">({campaign.status})</span>}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4">
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Signals</p>
            <h3 className="mt-1 text-2xl font-semibold">{keywords.length}</h3>
            <p className="mt-1 text-sm text-muted-foreground">Intent phrases and topic cues that seed community discovery.</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Coverage</p>
            <h3 className="mt-1 text-2xl font-semibold">{subreddits.length}</h3>
            <p className="mt-1 text-sm text-muted-foreground">Monitored communities with fit, activity, and rule context.</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Queue</p>
            <h3 className="mt-1 text-2xl font-semibold">{filteredOpps.length}</h3>
            <p className="mt-1 text-sm text-muted-foreground">Reply-ready conversations ranked by quality and contribution fit.</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Pattern Direction</CardTitle>
            <CardDescription>
              The current implementation is Reddit-native, but the workflow should support three reusable patterns: answer a question, join a discussion, and publish an original perspective.
            </CardDescription>
          </div>
          <CardAction>
            <Badge variant="default">Reddit live now</Badge>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Q and A answers</Badge>
            <Badge variant="secondary">Discussion replies</Badge>
            <Badge variant="secondary">Original posts</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          {/* Step Indicator */}
          <div className="flex items-center gap-2">
            {steps.map((s, i) => (
              <div key={i} className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium transition-colors",
                    s.done
                      ? "bg-primary text-primary-foreground"
                      : i === currentStep
                        ? "bg-primary/10 text-primary ring-2 ring-primary/30"
                        : "bg-muted text-muted-foreground"
                  )}
                >
                  {s.done ? "\u2713" : i + 1}
                </div>
                {i < steps.length - 1 && (
                  <div
                    className={cn(
                      "h-0.5 w-8",
                      s.done ? "bg-primary" : "bg-muted"
                    )}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-6">
            {steps.map((s, i) => (
              <span key={i} className="text-xs text-muted-foreground">{s.label}</span>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-medium">Step 1: Audience Signals ({keywords.length})</h3>
            <Button variant="outline" onClick={generateKeywords} disabled={generatingKeywords}>
              {generatingKeywords && <Loader2 className="h-4 w-4 animate-spin" />}
              Generate Signals
            </Button>
          </div>
          <div className="flex gap-2 mb-4">
            <Input
              type="text"
              value={newKeyword}
              onChange={(event) => setNewKeyword(event.target.value)}
              placeholder="Add a market phrase or audience signal"
              onKeyDown={(event) => event.key === "Enter" && void addKeyword()}
              className="flex-1"
            />
            <Button onClick={addKeyword} disabled={addingKeyword}>
              {addingKeyword && <Loader2 className="h-4 w-4 animate-spin" />}
              Add Signal
            </Button>
          </div>
          {keywords.length > 0 && (
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
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-medium">Step 2: Community Coverage ({subreddits.length})</h3>
            <Button
              variant="outline"
              onClick={discoverCommunities}
              disabled={discoveringCommunities || keywords.length === 0}
            >
              {discoveringCommunities && <Loader2 className="h-4 w-4 animate-spin" />}
              Discover Communities
            </Button>
          </div>
          {subreddits.length === 0 ? (
            <p className="text-sm text-muted-foreground">Add audience signals first, then discover communities that match those intents.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {subreddits.map((community) => (
                <Badge key={community.id} variant="secondary">
                  r/{community.name}
                  {community.fit_score !== undefined ? ` (${community.fit_score})` : ""}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-medium">Step 3: Conversation Queue ({filteredOpps.length})</h3>
            <div className="flex gap-2">
              {campaigns.length > 0 && (
                <select
                  value={campaignFilter}
                  onChange={(event) => setCampaignFilter(event.target.value)}
                  className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <option value="">All Campaigns</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              )}
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <option value="">All Statuses</option>
                <option value="new">New</option>
                <option value="saved">Saved</option>
                <option value="drafting">Drafting</option>
                <option value="posted">Posted</option>
                <option value="ignored">Ignored</option>
              </select>
              <Button onClick={runScan} disabled={scanning || subreddits.length === 0}>
                {scanning && <Loader2 className="h-4 w-4 animate-spin" />}
                {scanning ? "Scanning" : "Run Scan"}
              </Button>
            </div>
          </div>

          {filteredOpps.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="text-4xl">Q</div>
              <h3 className="mt-4 text-lg font-medium">
                {opportunities.length === 0 ? "No conversations found yet" : "No matches for this filter"}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {opportunities.length === 0
                  ? "Add signals, discover communities, then scan for reply-ready discussions."
                  : "Try changing the status filter."}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredOpps.map((opp) => (
                <div key={opp.id} className="rounded-lg border bg-card p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <PlatformIcon platform="reddit" />
                        <Badge variant="secondary">Live Source</Badge>
                        <a
                          href={redditUrl(opp.permalink)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-semibold text-foreground truncate hover:underline"
                        >
                          {opp.title}
                        </a>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Badge variant="outline">r/{opp.subreddit_name}</Badge>
                        {(opp.score_reasons || []).slice(0, 2).map((reason) => (
                          <Badge key={reason} variant="outline">
                            {reason}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <ScoreBadge score={opp.score || 0} />
                      <Button
                        onClick={() => generateReply(opp.id)}
                        disabled={generatingReply === opp.id}
                      >
                        {generatingReply === opp.id && <Loader2 className="h-4 w-4 animate-spin" />}
                        Draft Response
                      </Button>
                    </div>
                  </div>
                  {opp.body_excerpt && (
                    <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                      {opp.body_excerpt.substring(0, 220)}...
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Reply Draft Sheet */}
      <Sheet open={!!selectedOpp} onOpenChange={(open) => !open && setSelectedOpp(null)}>
        <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Draft Response: {selectedOpp?.title?.substring(0, 52) || ""}</SheetTitle>
            <SheetDescription>Edit and manage your generated reply draft.</SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-4">
            {selectedOpp?.permalink && (
              <div className="mb-4 rounded-lg bg-muted p-3">
                <a
                  href={redditUrl(selectedOpp.permalink)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  View original Reddit thread {"->"}
                </a>
                {selectedOpp.body_excerpt && (
                  <p className="mt-2 text-xs text-muted-foreground leading-snug">
                    {selectedOpp.body_excerpt.substring(0, 220)}...
                  </p>
                )}
              </div>
            )}

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
            {draftRationale && (
              <div className="mt-4 rounded-lg bg-muted p-4">
                <h4 className="text-sm font-medium">Why this response works</h4>
                <p className="mt-1 text-sm text-muted-foreground">{draftRationale}</p>
              </div>
            )}
          </div>

          <SheetFooter className="flex-row flex-wrap justify-end gap-2">
            <a href="/app/content">
              <Button variant="ghost">Review in Studio</Button>
            </a>
            <Button variant="outline" onClick={() => copyToClipboard(draftContent)}>
              Copy
            </Button>
            {selectedOpp?.permalink && (
              <Button onClick={() => copyAndOpenReddit(draftContent, selectedOpp.permalink)}>
                Copy and Open on Reddit
              </Button>
            )}
            <Button variant="outline" onClick={() => selectedOpp && markAsPosted(selectedOpp.id)}>
              Mark as Posted
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

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
