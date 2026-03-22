"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type MonitoredSubreddit } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

export default function SubredditsPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    fetchDashboard(token)
      .then((data) => { if (!ignore) setDashboard(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [token]);

  useEffect(() => {
    if (!token || !project) return;
    let ignore = false;
    apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${project.id}`, {}, token)
      .then((data) => { if (!ignore) setSubreddits(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [project, token]);

  async function refreshAnalysis(subredditId: number) {
    if (!token) return;
    try {
      setRefreshingId(subredditId);
      const updated = await apiRequest<MonitoredSubreddit>(`/v1/subreddits/${subredditId}/analyze`, { method: "POST" }, token);
      setSubreddits((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not refresh analysis.");
    } finally {
      setRefreshingId(null);
    }
  }

  return (
    <section className="card">
      <div className="eyebrow">Communities</div>
      <h2>Check which subreddits are worth your time</h2>
      <p>
        This page is only for review. If you are just getting started, you can stay on “Find posts” and come back here later.
      </p>
      {message ? <div className="notice">{message}</div> : null}
      <div className="item-list">
        {subreddits.length ? (
          subreddits.map((subreddit) => (
            <div key={subreddit.id} className="list-row">
              <div className="action-row">
                <strong>r/{subreddit.name}</strong>
                <button className="secondary-button" type="button" onClick={() => refreshAnalysis(subreddit.id)} disabled={refreshingId === subreddit.id}>
                  {refreshingId === subreddit.id ? "Working..." : "Refresh notes"}
                </button>
              </div>
              <p>{subreddit.description ?? subreddit.title ?? "No description available."}</p>
              <div className="badge-row">
                <span className="badge">Good fit: {subreddit.fit_score}/100</span>
                <span className="badge">Activity: {subreddit.activity_score}/100</span>
              </div>
              {subreddit.analyses[0] ? (
                <div className="notice">
                  <strong>What to do here:</strong> {subreddit.analyses[0].recommendation}
                  <br />
                  <span className="muted">People here: {subreddit.analyses[0].audience_signals?.join(", ") ?? "Not analyzed yet"}</span>
                </div>
              ) : null}
              {subreddit.rules_summary ? <p>Rules to watch: {subreddit.rules_summary}</p> : null}
            </div>
          ))
        ) : (
          <div className="empty-state">No communities yet. Use the “Find posts” page to discover them first.</div>
        )}
      </div>
    </section>
  );
}
