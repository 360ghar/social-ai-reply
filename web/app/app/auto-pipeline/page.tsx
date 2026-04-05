"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, Spinner } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSelectedProjectId } from "@/lib/use-selected-project";

// Types
interface PipelineRun {
  id: string;
  project_id: number;
  website_url: string;
  status: "pending" | "analyzing" | "generating_personas" | "discovering_keywords" | "finding_subreddits" | "scanning_opportunities" | "generating_drafts" | "ready" | "error";
  progress: number;
  personas_count: number;
  keywords_count: number;
  subreddits_count: number;
  opportunities_count: number;
  drafts_count: number;
  current_step: string;
  error_message?: string;
  created_at: string;
  completed_at?: string;
  results?: PipelineResults;
}

interface PipelineResults {
  brand_summary: string;
  personas: Persona[];
  keywords: Keyword[];
  subreddits: Subreddit[];
  opportunities: Opportunity[];
  drafts: Draft[];
}

interface Persona {
  name: string;
  role: string;
  summary: string;
  pain_points: string[];
}

interface Keyword {
  keyword: string;
  score: number;
  source: string;
}

interface Subreddit {
  name: string;
  fit_score: number;
  subscribers: number;
  description: string;
}

interface Opportunity {
  title: string;
  subreddit: string;
  score: number;
  author: string;
}

interface Draft {
  title: string;
  content: string;
  opportunity_title: string;
}

// Step definitions
const PIPELINE_STEPS = [
  { key: "analyzing", label: "Analyzing website" },
  { key: "generating_personas", label: "Generating personas" },
  { key: "discovering_keywords", label: "Discovering keywords" },
  { key: "finding_subreddits", label: "Finding subreddits" },
  { key: "scanning_opportunities", label: "Scanning opportunities" },
  { key: "generating_drafts", label: "Generating drafts" },
];

export default function AutoPipelinePage() {
  const router = useRouter();
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();

  // State
  const [urlInput, setUrlInput] = useState("");
  const [activeRun, setActiveRun] = useState<PipelineRun | null>(null);
  const [previousRuns, setPreviousRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [expanding, setExpanding] = useState<Record<string, boolean>>({});

  // Load previous runs on mount
  useEffect(() => {
    if (!token) return;
    loadPreviousRuns();
  }, [token, selectedProjectId]);

  // Poll active run
  useEffect(() => {
    if (!activeRun || activeRun.status === "ready" || activeRun.status === "error") return;
    if (!token) return;

    const interval = setInterval(() => {
      pollRun();
    }, 2000);

    return () => clearInterval(interval);
  }, [activeRun, token]);

  async function loadPreviousRuns() {
    setLoading(true);
    try {
      const url = selectedProjectId
        ? `/v1/auto-pipeline?project_id=${selectedProjectId}`
        : `/v1/auto-pipeline`;
      const runs = await apiRequest<{ items: PipelineRun[] }>(url, {}, token);
      setPreviousRuns(runs.items || []);
    } catch (error: any) {
      console.error(error);
    }
    setLoading(false);
  }

  async function pollRun() {
    if (!activeRun || !token) return;
    try {
      const updated = await apiRequest<PipelineRun>(
        `/v1/auto-pipeline/${activeRun.id}`,
        {},
        token
      );
      setActiveRun(updated);
    } catch (error: any) {
      console.error(error);
    }
  }

  async function handleLaunch() {
    if (!urlInput.trim()) {
      toast.warning("Please enter a website URL.");
      return;
    }

    if (!token) {
      toast.error("Please log in first.");
      return;
    }

    setLaunching(true);
    try {
      // Ensure URL has a scheme so the backend fetch doesn't choke.
      let url = urlInput.trim();
      if (!/^https?:\/\//i.test(url)) {
        url = `https://${url}`;
      }
      // project_id is optional — the backend will resolve or create a
      // default project when it is omitted or null.
      const body: Record<string, unknown> = {
        website_url: url,
      };
      if (selectedProjectId) {
        body.project_id = selectedProjectId;
      }
      const run = await apiRequest<PipelineRun>(
        "/v1/auto-pipeline/run",
        {
          method: "POST",
          body: JSON.stringify(body),
        },
        token
      );
      setActiveRun(run);
      setUrlInput("");
    } catch (error: any) {
      toast.error("Failed to launch pipeline", error.message || "Unknown error");
    }
    setLaunching(false);
  }

  async function handleExecuteAll() {
    if (!activeRun || activeRun.status !== "ready" || !token) return;

    try {
      await apiRequest(
        `/v1/auto-pipeline/${activeRun.id}/execute`,
        { method: "POST" },
        token
      );
      toast.success("Sales package executed! All drafts published.");
      setActiveRun(null);
      loadPreviousRuns();
    } catch (error: any) {
      toast.error("Failed to execute", error.message);
    }
  }

  const toggleExpand = (section: string) => {
    setExpanding((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // State 1: Input State
  if (!activeRun) {
    return (
      <div style={{ display: "grid", gap: 40, maxWidth: 1000, margin: "0 auto" }}>
        {/* Hero Section */}
        <div
          style={{
            textAlign: "center",
            padding: "60px 40px",
            background: "linear-gradient(135deg, var(--surface) 0%, var(--card) 100%)",
            borderRadius: 20,
            border: "1px solid var(--border)",
          }}
        >
          <h1 style={{ fontSize: 44, fontWeight: 700, marginBottom: 12, color: "var(--ink)" }}>
            Auto-Pipeline
          </h1>
          <p style={{ fontSize: 16, color: "var(--muted)", marginBottom: 40, maxWidth: 600, margin: "0 auto 40px" }}>
            Enter any website URL and we'll build your complete engagement strategy
          </p>

          {/* URL Input */}
          <div style={{ display: "grid", gap: 12, marginBottom: 24 }}>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLaunch()}
              placeholder="https://example.com"
              style={{
                padding: "16px 20px",
                fontSize: 16,
                border: "2px solid var(--border)",
                borderRadius: 12,
                background: "var(--card)",
                color: "var(--ink)",
                fontFamily: "inherit",
              }}
            />
            <Button
              loading={launching}
              onClick={handleLaunch}
              style={{
                padding: "14px 24px",
                fontSize: 15,
                fontWeight: 600,
                width: "100%",
              }}
            >
              Launch Pipeline
            </Button>
          </div>
        </div>

        {/* Previous Runs */}
        {!loading && previousRuns.length > 0 && (
          <section>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: "var(--ink)" }}>
              Previous Pipeline Runs
            </h3>
            <div style={{ display: "grid", gap: 10 }}>
              {previousRuns.map((run) => (
                <div
                  key={run.id}
                  onClick={() => setActiveRun(run)}
                  style={{
                    padding: "16px",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                    background: "var(--card)",
                    cursor: "pointer",
                    transition: "all 0.2s",
                    display: "grid",
                    gridTemplateColumns: "1fr auto auto",
                    alignItems: "center",
                    gap: 16,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "var(--surface)";
                    e.currentTarget.style.borderColor = "var(--accent)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "var(--card)";
                    e.currentTarget.style.borderColor = "var(--border)";
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, color: "var(--ink)", fontSize: 14, marginBottom: 4 }}>
                      {run.website_url}
                    </div>
                    <div style={{ fontSize: 13, color: "var(--muted)" }}>
                      {new Date(run.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--accent)" }}>
                      {run.drafts_count} drafts
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "4px 12px",
                      borderRadius: 6,
                      background:
                        run.status === "ready"
                          ? "rgba(34, 197, 94, 0.1)"
                          : run.status === "error"
                            ? "rgba(239, 68, 68, 0.1)"
                            : "rgba(168, 162, 158, 0.1)",
                      color:
                        run.status === "ready"
                          ? "#22c55e"
                          : run.status === "error"
                            ? "#ef4444"
                            : "#a8a29e",
                      fontSize: 12,
                      fontWeight: 600,
                      textTransform: "capitalize",
                    }}
                  >
                    {run.status.replace(/_/g, " ")}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    );
  }

  // State 2: Running State
  if (activeRun && activeRun.status !== "ready" && activeRun.status !== "error") {
    const progressPercent = activeRun.progress || 0;
    const currentStepIndex = PIPELINE_STEPS.findIndex((s) => s.key === activeRun.status);
    const completedSteps = currentStepIndex >= 0 ? currentStepIndex : 0;

    return (
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 20px" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <h2 style={{ fontSize: 32, fontWeight: 700, marginBottom: 8 }}>Building Your Sales Package</h2>
          <p style={{ fontSize: 14, color: "var(--muted)" }}>{activeRun.website_url}</p>
        </div>

        {/* Progress Bar */}
        <div style={{ marginBottom: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)" }}>Progress</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)" }}>{progressPercent}%</div>
          </div>
          <div
            style={{
              width: "100%",
              height: 8,
              background: "var(--surface)",
              borderRadius: 4,
              overflow: "hidden",
              border: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                width: `${progressPercent}%`,
                height: "100%",
                background: "var(--accent)",
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>

        {/* Steps Checklist */}
        <div
          style={{
            padding: 20,
            background: "var(--card)",
            borderRadius: 12,
            border: "1px solid var(--border)",
            marginBottom: 32,
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", marginBottom: 16 }}>
            Pipeline Steps
          </div>
          <div style={{ display: "grid", gap: 12 }}>
            {PIPELINE_STEPS.map((step, idx) => {
              const isDone = idx < completedSteps;
              const isCurrent = idx === completedSteps;

              return (
                <div
                  key={step.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    opacity: isDone || isCurrent ? 1 : 0.4,
                  }}
                >
                  <div
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: 12,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 12,
                      fontWeight: 700,
                      background: isDone ? "var(--accent)" : isCurrent ? "var(--surface)" : "var(--border)",
                      color: isDone ? "white" : isCurrent ? "var(--accent)" : "var(--muted)",
                      border: isCurrent ? "2px solid var(--accent)" : "none",
                    }}
                  >
                    {isDone ? "✓" : isCurrent ? <Spinner size="sm" /> : idx + 1}
                  </div>
                  <div style={{ fontSize: 14, fontWeight: isDone || isCurrent ? 600 : 400, color: "var(--ink)" }}>
                    {step.label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Live Counters */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
            gap: 12,
            marginBottom: 32,
          }}
        >
          <CounterCard label="Personas" value={activeRun.personas_count} />
          <CounterCard label="Keywords" value={activeRun.keywords_count} />
          <CounterCard label="Subreddits" value={activeRun.subreddits_count} />
          <CounterCard label="Opportunities" value={activeRun.opportunities_count} />
          <CounterCard label="Drafts" value={activeRun.drafts_count} />
        </div>

        {/* Cancel Button */}
        <div style={{ textAlign: "center" }}>
          <Button
            variant="secondary"
            onClick={() => {
              setActiveRun(null);
              loadPreviousRuns();
            }}
          >
            Cancel Pipeline
          </Button>
        </div>
      </div>
    );
  }

  // State 3: Results State
  if (activeRun && activeRun.status === "ready" && activeRun.results) {
    const results = activeRun.results;

    return (
      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 20px" }}>
        {/* Success Banner */}
        <div
          style={{
            padding: "24px",
            background: "rgba(34, 197, 94, 0.1)",
            border: "1px solid rgba(34, 197, 94, 0.3)",
            borderRadius: 12,
            marginBottom: 32,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 700, color: "#22c55e", marginBottom: 4 }}>
            ✓ Your Sales Package is Ready!
          </div>
          <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 0 }}>
            {activeRun.website_url}
          </p>
        </div>

        {/* Summary Cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
            gap: 12,
            marginBottom: 32,
          }}
        >
          <SummaryCard label="Personas" value={results.personas.length} />
          <SummaryCard label="Keywords" value={results.keywords.length} />
          <SummaryCard label="Subreddits" value={results.subreddits.length} />
          <SummaryCard label="Opportunities" value={results.opportunities.length} />
          <SummaryCard label="Drafts" value={results.drafts.length} />
        </div>

        {/* Expandable Sections */}
        <div style={{ display: "grid", gap: 16, marginBottom: 32 }}>
          {/* Brand Summary */}
          <ExpandableSection
            title="Brand Summary"
            isExpanded={expanding["brand_summary"]}
            onToggle={() => toggleExpand("brand_summary")}
          >
            <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink)", margin: 0 }}>
              {results.brand_summary}
            </p>
          </ExpandableSection>

          {/* Personas */}
          <ExpandableSection
            title={`Personas (${results.personas.length})`}
            isExpanded={expanding["personas"]}
            onToggle={() => toggleExpand("personas")}
          >
            <div style={{ display: "grid", gap: 12 }}>
              {results.personas.map((persona, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: 12,
                    background: "var(--surface)",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 14 }}>
                    {persona.name} {persona.role && `(${persona.role})`}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--muted)", marginBottom: 8 }}>
                    {persona.summary}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--muted)" }}>
                    <div style={{ marginBottom: 4 }}>
                      <strong>Pain points:</strong> {persona.pain_points.join(", ")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ExpandableSection>

          {/* Keywords */}
          <ExpandableSection
            title={`Keywords (${results.keywords.length})`}
            isExpanded={expanding["keywords"]}
            onToggle={() => toggleExpand("keywords")}
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Keyword</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Score</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {results.keywords.map((kw, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px", color: "var(--ink)" }}>{kw.keyword}</td>
                      <td style={{ padding: "8px", color: "var(--accent)", fontWeight: 600 }}>{kw.score}</td>
                      <td style={{ padding: "8px", color: "var(--muted)" }}>{kw.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ExpandableSection>

          {/* Subreddits */}
          <ExpandableSection
            title={`Subreddits (${results.subreddits.length})`}
            isExpanded={expanding["subreddits"]}
            onToggle={() => toggleExpand("subreddits")}
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Subreddit</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Fit Score</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Subscribers</th>
                  </tr>
                </thead>
                <tbody>
                  {results.subreddits.map((sub, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px", color: "var(--ink)", fontWeight: 500 }}>r/{sub.name}</td>
                      <td style={{ padding: "8px", color: "var(--accent)", fontWeight: 600 }}>{sub.fit_score}</td>
                      <td style={{ padding: "8px", color: "var(--muted)" }}>
                        {(sub.subscribers / 1000).toFixed(0)}k
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ExpandableSection>

          {/* Top Opportunities */}
          <ExpandableSection
            title={`Top Opportunities (${results.opportunities.length})`}
            isExpanded={expanding["opportunities"]}
            onToggle={() => toggleExpand("opportunities")}
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Title</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Subreddit</th>
                    <th style={{ padding: "8px", textAlign: "left", fontWeight: 600, color: "var(--muted)" }}>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {results.opportunities.slice(0, 10).map((opp, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "8px", color: "var(--ink)" }}>
                        <div style={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {opp.title}
                        </div>
                      </td>
                      <td style={{ padding: "8px", color: "var(--muted)" }}>r/{opp.subreddit}</td>
                      <td style={{ padding: "8px", color: "var(--accent)", fontWeight: 600 }}>{opp.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ExpandableSection>

          {/* Draft Replies */}
          <ExpandableSection
            title={`Draft Replies (${results.drafts.length})`}
            isExpanded={expanding["drafts"]}
            onToggle={() => toggleExpand("drafts")}
          >
            <div style={{ display: "grid", gap: 12 }}>
              {results.drafts.slice(0, 5).map((draft, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: 12,
                    background: "var(--surface)",
                    borderRadius: 8,
                    border: "1px solid var(--border)",
                  }}
                >
                  <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 6 }}>
                    Response to: <strong>{draft.opportunity_title}</strong>
                  </div>
                  <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--ink)", marginBottom: 8 }}>
                    {draft.content}
                  </div>
                </div>
              ))}
              {results.drafts.length > 5 && (
                <p style={{ fontSize: 13, color: "var(--muted)", margin: 0 }}>
                  +{results.drafts.length - 5} more drafts...
                </p>
              )}
            </div>
          </ExpandableSection>
        </div>

        {/* Action Buttons */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            padding: "24px",
            borderTop: "1px solid var(--border)",
            marginTop: 32,
          }}
        >
          <Button variant="secondary" onClick={() => router.push("/app/content")}>
            Review Individually
          </Button>
          <Button onClick={handleExecuteAll}>Execute All & Publish</Button>
        </div>
      </div>
    );
  }

  // Error State
  if (activeRun && activeRun.status === "error") {
    return (
      <div style={{ maxWidth: 600, margin: "0 auto", padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>⚠️</div>
        <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Pipeline Failed</h2>
        <p style={{ fontSize: 14, color: "var(--muted)", marginBottom: 16 }}>
          {activeRun.error_message || "An error occurred while running the pipeline."}
        </p>
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 24, opacity: 0.7 }}>
          Tip: Make sure the URL is publicly accessible and includes the full address (e.g. https://example.com).
        </p>
        <Button onClick={() => setActiveRun(null)}>Try Again</Button>
      </div>
    );
  }

  return null;
}

// Helper Components

function CounterCard({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        padding: 16,
        background: "var(--card)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, color: "var(--accent)", marginBottom: 4 }}>
        {value}
      </div>
      <div style={{ fontSize: 12, color: "var(--muted)", fontWeight: 500 }}>
        {label}
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div
      style={{
        padding: 16,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 28, fontWeight: 700, color: "var(--accent)", marginBottom: 6 }}>
        {value}
      </div>
      <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 500 }}>
        {label}
      </div>
    </div>
  );
}

interface ExpandableSectionProps {
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function ExpandableSection({ title, isExpanded, onToggle, children }: ExpandableSectionProps) {
  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 12,
        overflow: "hidden",
        background: "var(--card)",
      }}
    >
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "16px",
          background: "none",
          border: "none",
          textAlign: "left",
          fontSize: 14,
          fontWeight: 600,
          color: "var(--ink)",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          transition: "background 0.2s",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = "var(--surface)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "none";
        }}
      >
        {title}
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          {isExpanded ? "▼" : "▶"}
        </span>
      </button>
      {isExpanded && (
        <div
          style={{
            padding: "16px",
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
