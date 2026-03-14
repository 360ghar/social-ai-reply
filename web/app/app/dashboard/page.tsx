"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import {
  apiRequest,
  type BrandProfile,
  type Dashboard,
  type Keyword,
  type MonitoredSubreddit,
  type Opportunity,
  type Persona,
  type Project
} from "../../../lib/api";
import { setStoredProjectId } from "../../../lib/project";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

type ChecklistItem = {
  label: string;
  description: string;
  done: boolean;
  href: string;
};

export default function DashboardPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [businessName, setBusinessName] = useState("");
  const [businessDescription, setBusinessDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  async function loadDashboardAndDetails(selectedProjectId?: number) {
    if (!token) {
      return;
    }
    const dashboardPayload = await fetchDashboard(token);
    setDashboard(dashboardPayload);
    const currentProject =
      (selectedProjectId ? dashboardPayload.projects.find((item) => item.id === selectedProjectId) : null) ??
      getCurrentProject(dashboardPayload);

    if (!currentProject) {
      setBrand(null);
      setPersonas([]);
      setKeywords([]);
      setSubreddits([]);
      setOpportunities([]);
      return;
    }

    const [brandPayload, personaPayload, keywordPayload, subredditPayload, opportunityPayload] = await Promise.all([
      apiRequest<BrandProfile>(`/v1/brand/${currentProject.id}`, {}, token),
      apiRequest<Persona[]>(`/v1/personas?project_id=${currentProject.id}`, {}, token),
      apiRequest<Keyword[]>(`/v1/discovery/keywords?project_id=${currentProject.id}`, {}, token),
      apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${currentProject.id}`, {}, token),
      apiRequest<Opportunity[]>(`/v1/opportunities?project_id=${currentProject.id}`, {}, token)
    ]);

    setBrand(brandPayload);
    setPersonas(personaPayload);
    setKeywords(keywordPayload);
    setSubreddits(subredditPayload);
    setOpportunities(opportunityPayload);
  }

  useEffect(() => {
    if (!token) {
      return;
    }
    loadDashboardAndDetails().catch((err) => setError(err.message));
  }, [token]);

  const checklist = useMemo<ChecklistItem[]>(() => {
    return [
      {
        label: "Add your product",
        description: "Tell RedditFlow what you sell and paste your website.",
        done: Boolean(brand?.website_url || brand?.product_summary || brand?.summary),
        href: "/app/brand"
      },
      {
        label: "Add customer types",
        description: "Write down who you want to reach on Reddit.",
        done: personas.length > 0,
        href: "/app/persona"
      },
      {
        label: "Create search words",
        description: "Use customer language so we can find the right posts.",
        done: keywords.length > 0,
        href: "/app/discovery"
      },
      {
        label: "Pick communities",
        description: "Choose the subreddits worth checking first.",
        done: subreddits.length > 0,
        href: "/app/subreddits"
      },
      {
        label: "Find matching posts",
        description: "Run a scan and start drafting helpful replies.",
        done: opportunities.length > 0,
        href: "/app/discovery"
      }
    ];
  }, [brand, keywords.length, opportunities.length, personas.length, subreddits.length]);

  const nextStep = checklist.find((item) => !item.done) ?? checklist[checklist.length - 1];

  async function createBusiness(event: FormEvent) {
    event.preventDefault();
    if (!token || !businessName.trim()) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await apiRequest<Project>("/v1/projects", {
        method: "POST",
        body: JSON.stringify({ name: businessName.trim(), description: businessDescription.trim() || null })
      }, token);
      setStoredProjectId(created.id);
      setBusinessName("");
      setBusinessDescription("");
      await loadDashboardAndDetails(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the business.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="layout-two">
      <section className="card">
        <div className="eyebrow">Start here</div>
        <h2>{project ? `Use ${project.name} in 5 simple steps` : "Create your first business"}</h2>
        <p>
          {project
            ? "Follow these steps from top to bottom. You do not need to use every page right away."
            : "Everything starts with one business. Add its name now and you can fill in the rest step by step."}
        </p>
        {error ? <div className="notice">{error}</div> : null}

        {!project ? (
          <form className="item-list" onSubmit={createBusiness}>
            <label className="field">
              <span>Business name</span>
              <input value={businessName} onChange={(event) => setBusinessName(event.target.value)} placeholder="Acme Analytics" />
            </label>
            <label className="field">
              <span>What does this business sell?</span>
              <textarea
                value={businessDescription}
                onChange={(event) => setBusinessDescription(event.target.value)}
                placeholder="Short plain-English description"
              />
            </label>
            <button className="primary-button" type="submit" disabled={saving}>
              {saving ? "Creating..." : "Create business"}
            </button>
          </form>
        ) : (
          <>
            <div className="step-list">
              {checklist.map((item, index) => (
                <div key={item.label} className={item.done ? "step-row done" : "step-row"}>
                  <div className="step-marker">{index + 1}</div>
                  <div className="step-copy">
                    <strong>{item.label}</strong>
                    <p>{item.description}</p>
                  </div>
                  <div className="step-action">
                    <span className={item.done ? "badge success" : "badge"}>{item.done ? "Done" : "Next"}</span>
                    <Link href={item.href} className="secondary-button">
                      Open
                    </Link>
                  </div>
                </div>
              ))}
            </div>
            <div className="notice">
              <strong>Recommended next step:</strong> {nextStep.label}
              <br />
              <span className="muted">{nextStep.description}</span>
            </div>
          </>
        )}
      </section>

      <section className="card">
        <div className="eyebrow">Current business</div>
        <h2>{project?.name ?? "No business selected yet"}</h2>
        <p>{project?.description ?? "Create one business first, then follow the step-by-step checklist."}</p>
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="meta-label">Customer types</div>
            <strong>{personas.length}</strong>
          </div>
          <div className="kpi-card">
            <div className="meta-label">Search words</div>
            <strong>{keywords.length}</strong>
          </div>
          <div className="kpi-card">
            <div className="meta-label">Communities</div>
            <strong>{subreddits.length}</strong>
          </div>
          <div className="kpi-card">
            <div className="meta-label">Matches found</div>
            <strong>{opportunities.length}</strong>
          </div>
        </div>
        {brand?.summary ? (
          <div className="list-row">
            <strong>What RedditFlow knows about your product</strong>
            <p>{brand.summary}</p>
          </div>
        ) : null}
      </section>

      <section className="card">
        <div className="eyebrow">Best matches</div>
        <h2>Posts worth looking at first</h2>
        <div className="item-list">
          {opportunities.length ? (
            opportunities.slice(0, 6).map((opportunity) => (
              <a key={opportunity.id} href={opportunity.permalink} target="_blank" rel="noreferrer" className="opportunity-card">
                <div className="badge-row">
                  <span className="score-pill">Match {opportunity.score}/100</span>
                  <span className="badge">r/{opportunity.subreddit_name}</span>
                </div>
                <strong>{opportunity.title}</strong>
                <p>{opportunity.body_excerpt?.slice(0, 180) ?? "No preview available."}</p>
              </a>
            ))
          ) : (
            <div className="empty-state">
              Your matches will appear here after you add search words, choose communities, and run a scan.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
