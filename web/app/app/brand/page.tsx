"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { useToast } from "../../../components/toast";
import { Button, EmptyState, Spinner, Tabs, SkeletonCard } from "../../../components/ui";
import { apiRequest, type BrandProfile, type Dashboard } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";
import { useSelectedProjectId } from "../../../lib/use-selected-project";

export default function BrandPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [brand, setBrand] = useState<BrandProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isFilling, setIsFilling] = useState(false);
  const [activeTab, setActiveTab] = useState("profile");

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        toast.error("Failed to load", err.message);
      });
  }, [token, toast, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setIsLoading(true);
    apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {}, token)
      .then((data) => {
        setBrand(data);
        setIsLoading(false);
      })
      .catch((err) => {
        toast.error("Failed to load brand", err.message);
        setIsLoading(false);
      });
  }, [project, token, toast]);

  async function fillFromWebsite() {
    if (!token || !project || !brand?.website_url) {
      return;
    }
    setIsFilling(true);
    try {
      const analyzed = await apiRequest<BrandProfile>(`/v1/brand/${project.id}/analyze`, {
        method: "POST",
        body: JSON.stringify({ website_url: brand.website_url })
      }, token);
      setBrand(analyzed);
      toast.success("Website analyzed", "Details have been filled in from your website.");
    } catch (err) {
      toast.error("Analysis failed", err instanceof Error ? err.message : "Could not read the website.");
    } finally {
      setIsFilling(false);
    }
  }

  async function analyzeWebsite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await fillFromWebsite();
  }

  async function saveBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !project || !brand) {
      return;
    }
    setIsSaving(true);
    try {
      const payload = await apiRequest<BrandProfile>(`/v1/brand/${project.id}`, {
        method: "PUT",
        body: JSON.stringify(brand)
      }, token);
      setBrand(payload);
      toast.success("Saved", "Your brand details have been saved.");
    } catch (err) {
      toast.error("Save failed", err instanceof Error ? err.message : "Could not save product details.");
    } finally {
      setIsSaving(false);
    }
  }

  const calculateCompletion = () => {
    if (!brand) return 0;
    const fields = [
      brand.brand_name,
      brand.website_url,
      brand.product_summary,
      brand.target_audience,
      brand.voice_notes,
      brand.call_to_action,
      brand.reddit_username,
      brand.linkedin_url
    ];
    const filled = fields.filter(f => f && f.trim().length > 0).length;
    return Math.round((filled / fields.length) * 100);
  };

  const getCompletionColor = (pct: number) => {
    if (pct >= 80) return "badge-success";
    if (pct >= 50) return "badge-warning";
    return "badge-error";
  };

  if (isLoading) {
    return (
      <div className="split-grid">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (!brand) {
    return (
      <section className="card">
        <EmptyState
          icon="🏢"
          title="No brand yet"
          description="Go to Home and create a business first to get started."
        />
      </section>
    );
  }

  const completion = calculateCompletion();

  return (
    <div>
      <div className="card" style={{ marginBottom: "var(--space-lg)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-md)" }}>
          <div>
            <div className="eyebrow">Brand completeness</div>
            <h3 style={{ marginTop: "var(--space-sm)" }}>{brand.brand_name || "Your brand"}</h3>
          </div>
          <div className={`score-pill ${getCompletionColor(completion)}`} style={{ fontSize: "1.1em", padding: "0.5em 1em" }}>
            {completion}%
          </div>
        </div>
        <div className="progress-bar">
          <div
            className="progress-bar-fill"
            style={{
              width: `${completion}%`,
              backgroundColor: completion >= 80 ? "var(--success)" : completion >= 50 ? "var(--warning)" : "var(--error)",
              transition: "width 0.3s ease"
            }}
          />
        </div>
      </div>

      <div className="card">
        <Tabs
          tabs={[
            { key: "profile", label: "Brand Profile" },
            { key: "analysis", label: "Analysis" }
          ]}
          active={activeTab}
          onChange={setActiveTab}
        />

        {activeTab === "profile" && (
          <form onSubmit={saveBrand} style={{ paddingTop: "var(--space-lg)" }}>
            <div className="eyebrow">Your product</div>
            <h2>Tell us what you sell</h2>
            <p>Keep this simple. Plain English works best.</p>

            <label className="field">
              <span>Business name</span>
              <input
                value={brand.brand_name}
                onChange={(event) => setBrand({ ...brand, brand_name: event.target.value })}
                placeholder="e.g., Acme Inc."
              />
            </label>

            <label className="field">
              <span>Website URL</span>
              <input
                type="url"
                value={brand.website_url ?? ""}
                onChange={(event) => setBrand({ ...brand, website_url: event.target.value })}
                placeholder="https://example.com"
              />
            </label>

            <label className="field">
              <span>What do you sell?</span>
              <textarea
                value={brand.product_summary ?? ""}
                onChange={(event) => setBrand({ ...brand, product_summary: event.target.value })}
                placeholder="Describe your product or service in simple terms..."
                rows={3}
              />
            </label>

            <label className="field">
              <span>Who is it for?</span>
              <textarea
                value={brand.target_audience ?? ""}
                onChange={(event) => setBrand({ ...brand, target_audience: event.target.value })}
                placeholder="Who are your ideal customers? What do they look like?"
                rows={3}
              />
            </label>

            <label className="field">
              <span>How should replies sound?</span>
              <textarea
                value={brand.voice_notes ?? ""}
                onChange={(event) => setBrand({ ...brand, voice_notes: event.target.value })}
                placeholder="Tone, personality, values... e.g., 'professional but friendly'"
                rows={3}
              />
            </label>

            <label className="field">
              <span>What soft next step is okay to mention?</span>
              <textarea
                value={brand.call_to_action ?? ""}
                onChange={(event) => setBrand({ ...brand, call_to_action: event.target.value })}
                placeholder="e.g., 'Visit our blog', 'Email us', etc."
                rows={2}
              />
            </label>

            <label className="field">
              <span>Reddit username</span>
              <input
                value={brand.reddit_username ?? ""}
                onChange={(event) => setBrand({ ...brand, reddit_username: event.target.value })}
                placeholder="Optional: your Reddit username"
              />
            </label>

            <label className="field">
              <span>LinkedIn URL</span>
              <input
                type="url"
                value={brand.linkedin_url ?? ""}
                onChange={(event) => setBrand({ ...brand, linkedin_url: event.target.value })}
                placeholder="Optional: https://linkedin.com/company/..."
              />
            </label>

            <div className="action-row" style={{ marginTop: "var(--space-lg)" }}>
              <Button variant="primary" type="submit" loading={isSaving}>
                Save details
              </Button>
              <Button
                variant="secondary"
                type="button"
                onClick={fillFromWebsite}
                disabled={!brand.website_url}
                loading={isFilling}
              >
                Fill from website
              </Button>
            </div>
          </form>
        )}

        {activeTab === "analysis" && (
          <div style={{ paddingTop: "var(--space-lg)" }}>
            <div className="eyebrow">Website analysis</div>
            <h2>Fastest way to fill this page</h2>
            <p>Paste your website URL and click "Analyze website" to auto-fill fields, then edit as needed.</p>

            <form onSubmit={analyzeWebsite} style={{ marginTop: "var(--space-lg)" }}>
              <div className="action-row">
                <Button
                  variant="secondary"
                  type="submit"
                  disabled={!brand.website_url}
                  loading={isAnalyzing}
                >
                  Analyze website
                </Button>
              </div>
            </form>

            <div className="item-list" style={{ marginTop: "var(--space-lg)" }}>
              <div className="list-row">
                <strong>Summary</strong>
                <p style={{ color: "var(--muted)" }}>
                  {brand.summary && brand.summary.trim() ? brand.summary : "No summary yet. Analyze your website to fill this."}
                </p>
              </div>
              <div className="list-row">
                <strong>Call to action</strong>
                <p style={{ color: "var(--muted)" }}>
                  {brand.call_to_action && brand.call_to_action.trim() ? brand.call_to_action : "No CTA yet. Analyze your website to fill this."}
                </p>
              </div>
              <div className="list-row">
                <strong>Last website scan</strong>
                <p style={{ color: "var(--muted)" }}>
                  {brand.last_analyzed_at ? new Date(brand.last_analyzed_at).toLocaleDateString() : "Not analyzed yet"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
