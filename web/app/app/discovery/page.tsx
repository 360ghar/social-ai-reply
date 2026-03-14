"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type Keyword, type MonitoredSubreddit, type Opportunity, type ReplyDraft } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

export default function DiscoveryPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [drafts, setDrafts] = useState<Record<number, ReplyDraft>>({});
  const [draftingId, setDraftingId] = useState<number | null>(null);
  const [keywordInput, setKeywordInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  async function loadPageData(projectId: number) {
    if (!token) {
      return;
    }
    const [keywordRows, subredditRows, opportunityRows] = await Promise.all([
      apiRequest<Keyword[]>(`/v1/discovery/keywords?project_id=${projectId}`, {}, token),
      apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${projectId}`, {}, token),
      apiRequest<Opportunity[]>(`/v1/opportunities?project_id=${projectId}`, {}, token)
    ]);
    setKeywords(keywordRows);
    setSubreddits(subredditRows);
    setOpportunities(opportunityRows);
  }

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token).then(setDashboard).catch((err) => setMessage(err.message));
  }, [token]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    loadPageData(project.id).catch((err) => setMessage(err.message));
  }, [project, token]);

  async function createKeyword(event: FormEvent) {
    event.preventDefault();
    if (!token || !project || !keywordInput.trim()) {
      return;
    }
    try {
      const created = await apiRequest<Keyword>(`/v1/discovery/keywords?project_id=${project.id}`, {
        method: "POST",
        body: JSON.stringify({
          keyword: keywordInput.trim(),
          rationale: "Added by hand from the business owner",
          priority_score: 65,
          is_active: true
        })
      }, token);
      setKeywords((rows) => [created, ...rows]);
      setKeywordInput("");
      setMessage("Search word added.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not add the search word.");
    }
  }

  async function generateKeywords() {
    if (!token || !project) {
      return;
    }
    try {
      const created = await apiRequest<Keyword[]>(`/v1/discovery/keywords/generate?project_id=${project.id}`, {
        method: "POST",
        body: JSON.stringify({ count: 12 })
      }, token);
      setKeywords((rows) => [...created, ...rows.filter((row) => !created.some((item) => item.id === row.id))]);
      setMessage("Suggested search words created.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create search word suggestions.");
    }
  }

  async function discoverSubreddits() {
    if (!token || !project) {
      return;
    }
    try {
      const created = await apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits/discover?project_id=${project.id}`, {
        method: "POST",
        body: JSON.stringify({ max_subreddits: 8 })
      }, token);
      setSubreddits((rows) => [...created, ...rows.filter((row) => !created.some((item) => item.id === row.id))]);
      setMessage("Communities found. Review them below.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not find communities.");
    }
  }

  async function runScan() {
    if (!token || !project) {
      return;
    }
    try {
      await apiRequest("/v1/scans", {
        method: "POST",
        body: JSON.stringify({ project_id: project.id, search_window_hours: 72, max_posts_per_subreddit: 10 })
      }, token);
      await loadPageData(project.id);
      setMessage("Scan finished. Matching Reddit posts are listed below.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not scan Reddit right now.");
    }
  }

  async function writeReply(opportunityId: number) {
    if (!token) {
      return;
    }
    setDraftingId(opportunityId);
    try {
      const draft = await apiRequest<ReplyDraft>("/v1/drafts/replies", {
        method: "POST",
        body: JSON.stringify({ opportunity_id: opportunityId })
      }, token);
      setDrafts((rows) => ({ ...rows, [opportunityId]: draft }));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not write reply.");
    } finally {
      setDraftingId(null);
    }
  }

  if (!project) {
    return (
      <section className="card">
        <div className="empty-state">Go to Home first and create a business before trying to find posts.</div>
      </section>
    );
  }

  return (
    <div className="layout-two">
      <section className="card">
        <div className="eyebrow">How to use this page</div>
        <h2>Find Reddit posts in 3 simple actions</h2>
        <div className="step-list compact">
          <div className="step-row">
            <div className="step-marker">1</div>
            <div className="step-copy">
              <strong>Add search words</strong>
              <p>These are the words your customers might use when asking for help on Reddit.</p>
            </div>
          </div>
          <div className="step-row">
            <div className="step-marker">2</div>
            <div className="step-copy">
              <strong>Find communities</strong>
              <p>Pick the best subreddits to watch.</p>
            </div>
          </div>
          <div className="step-row">
            <div className="step-marker">3</div>
            <div className="step-copy">
              <strong>Find matching posts</strong>
              <p>Run the scan, open the best thread, and generate a helpful reply draft.</p>
            </div>
          </div>
        </div>
        {message ? <div className="notice">{message}</div> : null}
      </section>

      <section className="card">
        <div className="eyebrow">Search words</div>
        <h2>What should we look for?</h2>
        <p>Start with 5 to 10 phrases a customer might write when they need help.</p>
        <form className="inline-form" onSubmit={createKeyword}>
          <input value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} placeholder="example: best crm for small team" />
          <button className="secondary-button" type="submit">Add word</button>
          <button className="primary-button" type="button" onClick={generateKeywords}>Create suggestions</button>
        </form>
        <div className="table-list">
          {keywords.length ? (
            keywords.map((keyword) => (
              <div key={keyword.id} className="list-row">
                <strong>{keyword.keyword}</strong>
                <p>{keyword.rationale ?? "No note saved."}</p>
              </div>
            ))
          ) : (
            <div className="empty-state">No search words yet. Add one above or click "Create suggestions".</div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="eyebrow">Communities and scan</div>
        <h2>Where should we search?</h2>
        <div className="action-row">
          <button className="primary-button" type="button" onClick={discoverSubreddits}>Find communities</button>
          <button className="secondary-button" type="button" onClick={runScan}>Find matching posts</button>
        </div>
        <div className="table-list">
          {subreddits.length ? (
            subreddits.map((subreddit) => (
              <div key={subreddit.id} className="list-row">
                <strong>r/{subreddit.name}</strong>
                <p>{subreddit.description ?? subreddit.title ?? "No description available."}</p>
                <div className="badge-row">
                  <span className="badge">Good fit: {subreddit.fit_score}/100</span>
                  <span className="badge">Activity: {subreddit.activity_score}/100</span>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">No communities yet. Click "Find communities" after adding search words.</div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="eyebrow">Matching posts</div>
        <h2>Best Reddit posts to reply to</h2>
        <div className="item-list">
          {opportunities.length ? (
            opportunities.map((opportunity) => (
              <div key={opportunity.id} className="opportunity-card">
                <div className="badge-row">
                  <span className="score-pill">Match {opportunity.score}/100</span>
                  <span className="badge">r/{opportunity.subreddit_name}</span>
                </div>
                <strong>{opportunity.title}</strong>
                <p>{opportunity.body_excerpt?.slice(0, 220) ?? "No preview available."}</p>
                {opportunity.score_reasons.length ? (
                  <p className="muted">Why it matches: {opportunity.score_reasons.join(" ")}</p>
                ) : null}
                <div className="action-row">
                  <a href={opportunity.permalink} target="_blank" rel="noreferrer" className="secondary-button">
                    Open Reddit post
                  </a>
                  <button className="primary-button" type="button" onClick={() => writeReply(opportunity.id)} disabled={draftingId === opportunity.id}>
                    {draftingId === opportunity.id ? "Writing..." : "Write a reply"}
                  </button>
                </div>
                {drafts[opportunity.id] ? (
                  <div className="notice">
                    <strong>Reply draft</strong>
                    <p>{drafts[opportunity.id].content}</p>
                  </div>
                ) : null}
              </div>
            ))
          ) : (
            <div className="empty-state">Run "Find matching posts" and your best Reddit threads will appear here.</div>
          )}
        </div>
      </section>
    </div>
  );
}
