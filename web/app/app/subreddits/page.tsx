"use client";

import { useEffect, useState } from "react";

import { Button, EmptyState, KpiCard, ScoreBadge, Tabs, Spinner } from "../../../components/ui";
import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type MonitoredSubreddit } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";
import { useSelectedProjectId } from "../../../lib/use-selected-project";

type SortOption = "fit-score" | "activity-score" | "name";

export default function SubredditsPage() {
  const { token } = useAuth();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("fit-score");
  const [activeTab, setActiveTab] = useState<"all" | "top">("all");

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        setMessage(err.message);
        setLoading(false);
      });
  }, [token, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setLoading(true);
    apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${project.id}`, {}, token)
      .then(setSubreddits)
      .catch((err) => setMessage(err.message))
      .finally(() => setLoading(false));
  }, [project, token]);

  async function refreshAnalysis(subredditId: number) {
    if (!token) {
      return;
    }
    setRefreshingId(subredditId);
    try {
      const updated = await apiRequest<MonitoredSubreddit>(
        `/v1/subreddits/${subredditId}/analyze`,
        { method: "POST" },
        token
      );
      setSubreddits((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setMessage("Analysis refreshed");
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setRefreshingId(null);
    }
  }

  // Filter communities based on tab and search query
  const filteredSubreddits = subreddits
    .filter((s) => {
      if (activeTab === "top" && s.fit_score < 70) {
        return false;
      }
      return s.name.toLowerCase().includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "fit-score":
          return b.fit_score - a.fit_score;
        case "activity-score":
          return b.activity_score - a.activity_score;
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

  // Calculate KPI metrics
  const avgFitScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.fit_score, 0) / subreddits.length) : 0;
  const avgActivityScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.activity_score, 0) / subreddits.length) : 0;
  const activeCount = subreddits.filter((s) => s.is_active).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Header Section */}
      <section className="card">
        <div className="eyebrow">Community Coverage</div>
        <h2>Review which communities deserve active engagement</h2>
        <p>
          Today this page is Reddit-specific, but the scoring model is the right shape for a broader product: fit, activity, moderation risk, and audience signals should work across forums, Q and A spaces, and social comment surfaces.
        </p>
        <div className="badge-row" style={{ marginTop: 16 }}>
          <span className="badge badge-info">Reddit live now</span>
          <span className="badge">Q and A pattern ready</span>
          <span className="badge">Forum pattern ready</span>
        </div>
        {message && <div className="notice">{message}</div>}
      </section>

      {/* KPI Cards */}
      {!loading && subreddits.length > 0 && (
        <div className="section-grid">
          <KpiCard label="Total Communities" value={subreddits.length} />
          <KpiCard label="Avg Fit Score" value={avgFitScore} />
          <KpiCard label="Avg Activity Score" value={avgActivityScore} />
          <KpiCard label="Active" value={activeCount} />
        </div>
      )}

      {/* Communities List */}
      <section className="card">
        {/* Controls */}
        {!loading && subreddits.length > 0 && (
          <div style={{ marginBottom: "1.5rem" }}>
            {/* Tabs */}
            <div className="tabs" style={{ marginBottom: "1.5rem" }}>
              <button
                className={`tab ${activeTab === "all" ? "active" : ""}`}
                onClick={() => setActiveTab("all")}
              >
                All Communities
              </button>
              <button
                className={`tab ${activeTab === "top" ? "active" : ""}`}
                onClick={() => setActiveTab("top")}
              >
                Top Performers
              </button>
            </div>

            {/* Search and Sort */}
            <div style={{ display: "flex", gap: "1rem", marginBottom: "1.5rem" }}>
              <div className="field" style={{ flex: 1 }}>
                <input
                  type="text"
                  placeholder="Filter by subreddit name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{ width: "100%" }}
                />
              </div>
              <div className="field">
                <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortOption)}>
                  <option value="fit-score">Sort by Fit Score</option>
                  <option value="activity-score">Sort by Activity Score</option>
                  <option value="name">Sort by Name</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
            <Spinner />
          </div>
        )}

        {/* Communities */}
        {!loading && filteredSubreddits.length > 0 && (
          <div className="item-list">
            {filteredSubreddits.map((subreddit) => (
              <div key={subreddit.id} className="card" style={{ marginBottom: "1rem" }}>
                <div className="action-row" style={{ marginBottom: "1rem" }}>
                  <div>
                    <strong style={{ fontSize: "1.1rem" }}>r/{subreddit.name}</strong>
                    {subreddit.title && <p style={{ margin: "0.25rem 0 0 0", color: "var(--text-secondary)" }}>{subreddit.title}</p>}
                  </div>
                  <Button
                    onClick={() => refreshAnalysis(subreddit.id)}
                    disabled={refreshingId === subreddit.id}
                    variant="secondary"
                  >
                    {refreshingId === subreddit.id ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
                        <Spinner size="sm" />
                        Refreshing...
                      </span>
                    ) : (
                      "Refresh Analysis"
                    )}
                  </Button>
                </div>

                {/* Description */}
                {subreddit.description && (
                  <p style={{ margin: "0 0 1rem 0", color: "var(--text-secondary)" }}>
                    {subreddit.description}
                  </p>
                )}

                {/* Scores */}
                <div className="badge-row" style={{ marginBottom: "1rem" }}>
                  <span className="badge">Fit</span>
                  <ScoreBadge score={subreddit.fit_score} />
                  <span className="badge">Activity</span>
                  <ScoreBadge score={subreddit.activity_score} />
                </div>

                {/* Subscriber Count */}
                <div style={{ marginBottom: "1rem", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                  {subreddit.subscribers.toLocaleString()} subscribers
                </div>

                {/* Analysis */}
                {subreddit.analyses[0] && (
                  <div className="notice" style={{ marginBottom: "1rem" }}>
                    <strong>Recommendation:</strong> {subreddit.analyses[0].recommendation}
                    {subreddit.analyses[0].audience_signals.length > 0 && (
                      <>
                        <br />
                        <strong style={{ fontSize: "0.9rem" }}>Audience signals:</strong> {subreddit.analyses[0].audience_signals.join(", ")}
                      </>
                    )}
                  </div>
                )}

                {/* Rules Summary */}
                {subreddit.rules_summary && (
                  <div style={{ fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                    <strong>Rules to watch:</strong> {subreddit.rules_summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Empty States */}
        {!loading && filteredSubreddits.length === 0 && subreddits.length === 0 && (
          <EmptyState
            title="No communities yet"
            description="Use the Find posts page to discover communities first."
          />
        )}

        {!loading && filteredSubreddits.length === 0 && subreddits.length > 0 && (
          <EmptyState
            title="No communities match your filter"
            description="Try adjusting your search or sort options."
          />
        )}
      </section>
    </div>
  );
}
