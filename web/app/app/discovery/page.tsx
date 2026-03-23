"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import {
  Button,
  EmptyState,
  StepIndicator,
  ScoreBadge,
  PlatformIcon,
  Spinner,
  Drawer,
} from "@/components/ui";
import { ConfirmModal } from "@/components/modal";
import { apiRequest } from "@/lib/api";

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
  const [scoreSort, setScoreSort] = useState(true);
  const [project, setProject] = useState<ProjectContext | null>(null);

  useEffect(() => {
    if (!token) return;
    loadAll();
  }, [token]);

  async function loadAll() {
    setLoading(true);
    try {
      // First try to get current project from dashboard
      const dashRes = await apiRequest<any>("/v1/dashboard", {}, token);
      const currentProject =
        dashRes.projects && dashRes.projects.length > 0
          ? dashRes.projects[0]
          : null;

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

      if (kwRes.status === "fulfilled") setKeywords(kwRes.value || []);
      if (subRes.status === "fulfilled") setSubreddits(subRes.value || []);
      if (oppRes.status === "fulfilled") setOpportunities(oppRes.value || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }

  async function addKeyword() {
    if (!newKeyword.trim() || !project) return;
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
      toast.success("Keyword added!");
      loadAll();
    } catch (e: any) {
      toast.error("Failed to add keyword", e.message);
    }
    setAddingKeyword(false);
  }

  async function generateKeywords() {
    if (!project) return;
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
      toast.success("Keywords generated!");
      loadAll();
    } catch (e: any) {
      toast.error("Failed to generate", e.message);
    }
    setGeneratingKeywords(false);
  }

  async function discoverCommunities() {
    if (!project) return;
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
      toast.success("Communities discovered!");
      loadAll();
    } catch (e: any) {
      toast.error("Failed to discover", e.message);
    }
    setDiscoveringCommunities(false);
  }

  async function runScan() {
    if (!project) return;
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
      toast.success("Scan complete!", "Check your opportunities below.");
      loadAll();
    } catch (e: any) {
      toast.error("Scan failed", e.message);
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
      setSelectedOpp(opportunities.find((o) => o.id === oppId) || null);
      toast.success("Reply drafted!");
    } catch (e: any) {
      toast.error("Could not generate reply", e.message);
    }
    setGeneratingReply(null);
  }

  async function deleteItem() {
    if (!deleteTarget) return;
    try {
      await apiRequest(
        `/v1/discovery/${deleteTarget.type}/${deleteTarget.id}`,
        { method: "DELETE" },
        token
      );
      toast.success(`${deleteTarget.name} deleted`);
      setDeleteTarget(null);
      loadAll();
    } catch (e: any) {
      toast.error("Delete failed", e.message);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  }

  function redditUrl(permalink: string) {
    if (permalink.startsWith("http")) return permalink;
    return `https://www.reddit.com${permalink}`;
  }

  function copyAndOpenReddit(text: string, permalink: string) {
    navigator.clipboard.writeText(text);
    window.open(redditUrl(permalink), "_blank");
    toast.success("Reply copied! Reddit is opening — paste your reply there.");
  }

  async function markAsPosted(oppId: number) {
    try {
      await apiRequest(`/v1/opportunities/${oppId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: "POSTED" }),
      }, token);
      toast.success("Marked as posted!");
      setSelectedOpp(null);
      loadAll();
    } catch (e: any) {
      toast.error("Could not update status", e.message);
    }
  }

  const steps = [
    { label: "Add Keywords", done: keywords.length > 0 },
    { label: "Find Communities", done: subreddits.length > 0 },
    { label: "Scan for Posts", done: opportunities.length > 0 },
  ];
  const currentStep = steps.findIndex((s) => !s.done);

  let filteredOpps = [...opportunities];
  if (statusFilter) filteredOpps = filteredOpps.filter((o) => o.status === statusFilter);
  if (scoreSort) filteredOpps.sort((a, b) => (b.score || 0) - (a.score || 0));

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: 60 }}>
        <Spinner size="lg" />
      </div>
    );
  }

  if (!project) {
    return (
      <div>
        <EmptyState
          icon="📋"
          title="No project selected"
          description="Go to Dashboard first and create a business before trying to find posts."
        />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 className="page-title">Find Opportunities</h2>
        <p className="text-muted">
          Discover Reddit threads where your expertise fits, then draft helpful replies.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 32, padding: 20 }}>
        <StepIndicator steps={steps} currentStep={currentStep >= 0 ? currentStep : 2} />
      </div>

      {/* Step 1: Keywords */}
      <div className="card" style={{ marginBottom: 24, padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">
            Step 1: Keywords ({keywords.length})
          </h3>
          <Button variant="secondary" loading={generatingKeywords} onClick={generateKeywords}>
            AI Suggest
          </Button>
        </div>
        <div className="inline-form" style={{ marginBottom: 16, display: "flex", gap: 8 }}>
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            placeholder="Add a keyword..."
            onKeyDown={(e) => e.key === "Enter" && addKeyword()}
            style={{ flex: 1 }}
          />
          <Button loading={addingKeyword} onClick={addKeyword}>
            Add
          </Button>
        </div>
        {keywords.length > 0 && (
          <div className="flex gap-sm" style={{ flexWrap: "wrap" }}>
            {keywords.map((k) => (
              <span key={k.id} className="badge" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                {k.keyword}
                <button
                  onClick={() =>
                    setDeleteTarget({ type: "keywords", id: k.id, name: k.keyword })
                  }
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    marginLeft: 4,
                    fontSize: 12,
                  }}
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Step 2: Communities */}
      <div className="card" style={{ marginBottom: 24, padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">
            Step 2: Communities ({subreddits.length})
          </h3>
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
          <p className="text-muted">
            Add keywords first, then discover matching communities.
          </p>
        ) : (
          <div className="flex gap-sm" style={{ flexWrap: "wrap" }}>
            {subreddits.map((s) => (
              <span key={s.id} className="badge" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                r/{s.name}
                {s.fit_score !== undefined && (
                  <span className="text-muted" style={{ fontSize: 10 }}>
                    ({s.fit_score})
                  </span>
                )}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Step 3: Scan + Results */}
      <div className="card" style={{ marginBottom: 24, padding: 24 }}>
        <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
          <h3 className="card-title">
            Step 3: Opportunities ({filteredOpps.length})
          </h3>
          <div className="flex gap-sm">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ minWidth: 120 }}
            >
              <option value="">All Status</option>
              <option value="NEW">New</option>
              <option value="SAVED">Saved</option>
              <option value="DRAFTING">Drafting</option>
              <option value="POSTED">Posted</option>
              <option value="IGNORED">Ignored</option>
            </select>
            <Button
              loading={scanning}
              onClick={runScan}
              disabled={subreddits.length === 0}
            >
              {scanning ? "Scanning..." : "Run Scan"}
            </Button>
          </div>
        </div>

        {filteredOpps.length === 0 ? (
          <EmptyState
            icon="🔍"
            title={
              opportunities.length === 0
                ? "No opportunities found yet"
                : "No matches for this filter"
            }
            description={
              opportunities.length === 0
                ? "Add keywords, discover communities, then run a scan."
                : "Try changing the status filter."
            }
          />
        ) : (
          <div className="item-list">
            {filteredOpps.map((opp) => (
              <div key={opp.id} className="list-row" style={{ padding: 12 }}>
                <div className="flex justify-between items-center">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-sm">
                      <PlatformIcon platform="reddit" />
                      <a
                        href={redditUrl(opp.permalink)}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontWeight: 600,
                          color: "var(--ink)",
                          textDecoration: "none",
                        }}
                      >
                        {(opp.title || "").substring(0, 80)}
                        {(opp.title || "").length > 80 ? "..." : ""}
                      </a>
                    </div>
                    <div className="flex gap-sm items-center" style={{ marginTop: 4 }}>
                      <span className="badge">r/{opp.subreddit_name}</span>
                      {opp.score_reasons && opp.score_reasons.length > 0 && (
                        <span className="text-muted" style={{ fontSize: 11 }}>
                          {opp.score_reasons.join(", ")}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-sm items-center">
                    <ScoreBadge score={opp.score || 0} />
                    <Button
                      variant="primary"
                      loading={generatingReply === opp.id}
                      onClick={() => generateReply(opp.id)}
                    >
                      Draft Reply
                    </Button>
                  </div>
                </div>
                {opp.body_excerpt && (
                  <p
                    className="text-muted"
                    style={{
                      marginTop: 8,
                      fontSize: 13,
                      lineHeight: 1.4,
                    }}
                  >
                    {opp.body_excerpt.substring(0, 200)}...
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Reply Draft Drawer */}
      <Drawer
        open={!!selectedOpp}
        onClose={() => setSelectedOpp(null)}
        title={`Reply to: ${selectedOpp?.title?.substring(0, 50) || ""}...`}
        footer={
          <div className="flex gap-md" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
            <button
              className="secondary-button"
              onClick={() => copyToClipboard(draftContent)}
            >
              📋 Copy
            </button>
            {selectedOpp?.permalink && (
              <Button
                variant="primary"
                onClick={() => copyAndOpenReddit(draftContent, selectedOpp.permalink)}
              >
                📋 Copy &amp; Open on Reddit
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => {
                if (selectedOpp) markAsPosted(selectedOpp.id);
              }}
            >
              ✅ Mark as Posted
            </Button>
          </div>
        }
      >
        {/* Link to original Reddit post */}
        {selectedOpp?.permalink && (
          <div style={{ marginBottom: 16, padding: 12, background: "var(--surface)", borderRadius: 8 }}>
            <a
              href={redditUrl(selectedOpp.permalink)}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent)", fontWeight: 500, fontSize: 13, textDecoration: "none" }}
            >
              🔗 View original post on Reddit →
            </a>
            {selectedOpp.body_excerpt && (
              <p className="text-muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.4 }}>
                {selectedOpp.body_excerpt.substring(0, 200)}...
              </p>
            )}
          </div>
        )}

        <div className="field">
          <label className="field-label">Generated Reply</label>
          <textarea
            rows={10}
            value={draftContent}
            onChange={(e) => setDraftContent(e.target.value)}
            style={{
              fontFamily: "inherit",
              fontSize: 13,
              lineHeight: 1.5,
            }}
          />
          <p className="field-help">{draftContent.length} characters</p>
        </div>
        {draftRationale && (
          <div className="card" style={{ backgroundColor: "var(--surface)", marginTop: 12, padding: 16 }}>
            <h4 className="field-label">Why this reply works:</h4>
            <p className="text-muted" style={{ fontSize: 13 }}>
              {draftRationale}
            </p>
          </div>
        )}
      </Drawer>

      {/* Delete Confirmation */}
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
