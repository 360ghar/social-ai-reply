"use client";

import { useEffect, useState } from "react";

import { ConfirmModal } from "@/components/modal";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import {
  Button,
  Drawer,
  EmptyState,
  PlatformIcon,
  ScoreBadge,
  Spinner,
  StepIndicator,
} from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/lib/use-selected-project";

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

export default function DiscoveryPage() {
  const { token } = useAuth();
  const toast = useToast();
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
      const [kwRes, subRes, oppRes] = await Promise.allSettled([
        apiRequest<Keyword[]>(`/v1/discovery/keywords?project_id=${projectId}`, {}, token),
        apiRequest<Subreddit[]>(`/v1/discovery/subreddits?project_id=${projectId}`, {}, token),
        apiRequest<Opportunity[]>(`/v1/opportunities?project_id=${projectId}`, {}, token),
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
    } catch (error) {
      console.error(error);
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
      toast.success("Signal added");
      await loadAll();
    } catch (error: any) {
      toast.error("Failed to add keyword", error.message);
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
      toast.success("Audience signals generated");
      await loadAll();
    } catch (error: any) {
      toast.error("Failed to generate", error.message);
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
      toast.success("Communities discovered");
      await loadAll();
    } catch (error: any) {
      toast.error("Failed to discover", error.message);
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
      toast.success("Scan complete", "Check the conversation queue below.");
      await loadAll();
    } catch (error: any) {
      toast.error("Scan failed", error.message);
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
      toast.success("Response drafted");
    } catch (error: any) {
      toast.error("Could not generate response", error.message);
    }
    setGeneratingReply(null);
  }

  async function deleteItem() {
    if (!deleteTarget) {
      return;
    }
    try {
      await apiRequest(`/v1/discovery/${deleteTarget.type}/${deleteTarget.id}`, { method: "DELETE" }, token);
      toast.success(`${deleteTarget.name} deleted`);
      setDeleteTarget(null);
      await loadAll();
    } catch (error: any) {
      toast.error("Delete failed", error.message);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }

  function redditUrl(permalink: string) {
    if (permalink.startsWith("http")) {
      return permalink;
    }
    return `https://www.reddit.com${permalink}`;
  }

  function copyAndOpenReddit(text: string, permalink: string) {
    navigator.clipboard.writeText(text);
    window.open(redditUrl(permalink), "_blank");
    toast.success("Draft copied. Reddit is opening so you can review and paste.");
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
      toast.success("Marked as posted");
      setSelectedOpp(null);
      await loadAll();
    } catch (error: any) {
      toast.error("Could not update status", error.message);
    }
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
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!project) {
    return (
      <EmptyState
        icon="PRJ"
        title="No project selected"
        description="Go to Command Center first and create a project before building an engagement workflow."
      />
    );
  }

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div>
        <div className="eyebrow">Engagement Workflow</div>
        <h2 className="page-title">Engagement Radar</h2>
        <p className="text-muted">
          Discover live Reddit conversations now using a workflow shaped for broader forum, Q and A, and social comment patterns over time.
        </p>
      </div>

      <div className="section-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))" }}>
        <div className="card">
          <div className="eyebrow">Signals</div>
          <h3 style={{ marginBottom: 8 }}>{keywords.length}</h3>
          <p>Intent phrases and topic cues that seed community discovery.</p>
        </div>
        <div className="card">
          <div className="eyebrow">Coverage</div>
          <h3 style={{ marginBottom: 8 }}>{subreddits.length}</h3>
          <p>Monitored communities with fit, activity, and rule context.</p>
        </div>
        <div className="card">
          <div className="eyebrow">Queue</div>
          <h3 style={{ marginBottom: 8 }}>{filteredOpps.length}</h3>
          <p>Reply-ready conversations ranked by quality and contribution fit.</p>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Pattern Direction</h3>
            <p className="card-description">
              The current implementation is Reddit-native, but the workflow should support three reusable patterns: answer a question, join a discussion, and publish an original perspective.
            </p>
          </div>
          <span className="badge badge-info">Reddit live now</span>
        </div>
        <div className="badge-row">
          <span className="badge">Q and A answers</span>
          <span className="badge">Discussion replies</span>
          <span className="badge">Original posts</span>
        </div>
      </div>

      <div className="card" style={{ padding: 20 }}>
        <StepIndicator steps={steps} currentStep={currentStep >= 0 ? currentStep : 2} />
      </div>

      <div className="card" style={{ padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">Step 1: Audience Signals ({keywords.length})</h3>
          <Button variant="secondary" loading={generatingKeywords} onClick={generateKeywords}>
            Generate Signals
          </Button>
        </div>
        <div className="inline-form" style={{ marginBottom: 16 }}>
          <input
            type="text"
            value={newKeyword}
            onChange={(event) => setNewKeyword(event.target.value)}
            placeholder="Add a market phrase or audience signal"
            onKeyDown={(event) => event.key === "Enter" && void addKeyword()}
          />
          <Button loading={addingKeyword} onClick={addKeyword}>
            Add Signal
          </Button>
        </div>
        {keywords.length > 0 && (
          <div className="badge-row">
            {keywords.map((keyword) => (
              <span key={keyword.id} className="badge" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                {keyword.keyword}
                <button
                  onClick={() => setDeleteTarget({ type: "keywords", id: keyword.id, name: keyword.keyword })}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }}
                >
                  x
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">Step 2: Community Coverage ({subreddits.length})</h3>
          <Button
            variant="secondary"
            loading={discoveringCommunities}
            onClick={discoverCommunities}
            disabled={keywords.length === 0}
          >
            Discover Communities
          </Button>
        </div>
        {subreddits.length === 0 ? (
          <p className="text-muted">Add audience signals first, then discover communities that match those intents.</p>
        ) : (
          <div className="badge-row">
            {subreddits.map((community) => (
              <span key={community.id} className="badge">
                r/{community.name}
                {community.fit_score !== undefined ? ` (${community.fit_score})` : ""}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">Step 3: Conversation Queue ({filteredOpps.length})</h3>
          <div className="flex gap-sm">
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} style={{ minWidth: 140 }}>
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="saved">Saved</option>
              <option value="drafting">Drafting</option>
              <option value="posted">Posted</option>
              <option value="ignored">Ignored</option>
            </select>
            <Button loading={scanning} onClick={runScan} disabled={subreddits.length === 0}>
              {scanning ? "Scanning" : "Run Scan"}
            </Button>
          </div>
        </div>

        {filteredOpps.length === 0 ? (
          <EmptyState
            icon="Q"
            title={opportunities.length === 0 ? "No conversations found yet" : "No matches for this filter"}
            description={
              opportunities.length === 0
                ? "Add signals, discover communities, then scan for reply-ready discussions."
                : "Try changing the status filter."
            }
          />
        ) : (
          <div className="item-list">
            {filteredOpps.map((opp) => (
              <div key={opp.id} className="list-row">
                <div className="flex justify-between items-center">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-sm">
                      <PlatformIcon platform="reddit" />
                      <span className="badge">Live Source</span>
                      <a
                        href={redditUrl(opp.permalink)}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ fontWeight: 600, color: "var(--ink)" }}
                      >
                        {opp.title}
                      </a>
                    </div>
                    <div className="badge-row" style={{ marginTop: 8 }}>
                      <span className="badge">r/{opp.subreddit_name}</span>
                      {(opp.score_reasons || []).slice(0, 2).map((reason) => (
                        <span key={reason} className="badge">
                          {reason}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-sm items-center">
                    <ScoreBadge score={opp.score || 0} />
                    <Button
                      variant="primary"
                      loading={generatingReply === opp.id}
                      onClick={() => generateReply(opp.id)}
                    >
                      Draft Response
                    </Button>
                  </div>
                </div>
                {opp.body_excerpt && (
                  <p className="text-muted" style={{ marginTop: 8, fontSize: 13, lineHeight: 1.5 }}>
                    {opp.body_excerpt.substring(0, 220)}...
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <Drawer
        open={!!selectedOpp}
        onClose={() => setSelectedOpp(null)}
        title={`Draft Response: ${selectedOpp?.title?.substring(0, 52) || ""}`}
        footer={
          <div className="flex gap-md" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
            <a href="/app/content" className="ghost-button" style={{ textDecoration: "none" }}>
              Review in Studio
            </a>
            <button className="secondary-button" onClick={() => copyToClipboard(draftContent)}>
              Copy
            </button>
            {selectedOpp?.permalink && (
              <Button variant="primary" onClick={() => copyAndOpenReddit(draftContent, selectedOpp.permalink)}>
                Copy and Open on Reddit
              </Button>
            )}
            <Button variant="secondary" onClick={() => selectedOpp && markAsPosted(selectedOpp.id)}>
              Mark as Posted
            </Button>
          </div>
        }
      >
        {selectedOpp?.permalink && (
          <div style={{ marginBottom: 16, padding: 12, background: "var(--surface)", borderRadius: 8 }}>
            <a
              href={redditUrl(selectedOpp.permalink)}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)", fontWeight: 500, fontSize: 13 }}
            >
              View original Reddit thread {"->"}
            </a>
            {selectedOpp.body_excerpt && (
              <p className="text-muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.4 }}>
                {selectedOpp.body_excerpt.substring(0, 220)}...
              </p>
            )}
          </div>
        )}

        <div className="field">
          <label className="field-label">Generated Response</label>
          <textarea
            rows={10}
            value={draftContent}
            onChange={(event) => setDraftContent(event.target.value)}
            style={{ fontSize: 13, lineHeight: 1.5 }}
          />
          <p className="field-help">{draftContent.length} characters</p>
        </div>
        {draftRationale && (
          <div className="card" style={{ backgroundColor: "var(--surface)", marginTop: 12, padding: 16 }}>
            <h4 className="field-label">Why this response works</h4>
            <p className="text-muted" style={{ fontSize: 13 }}>{draftRationale}</p>
          </div>
        )}
      </Drawer>

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={deleteItem}
        title={`Delete ${deleteTarget?.name || ""}?`}
        message="This action cannot be undone. Are you sure?"
        confirmText="Delete"
        danger
      />
    </div>
  );
}
