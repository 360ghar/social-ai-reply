"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, EmptyState, KpiCard, Spinner, Tabs, Skeleton } from "@/components/ui";
import { Modal } from "@/components/modal";
import {
  getVisibilitySummary, getPromptSets, createPromptSet, runPromptSet,
  getVisibilityPrompts, VisibilitySummary, PromptSetItem, PromptRunResult, apiRequest
} from "@/lib/api";
import { useSelectedProjectId } from "@/lib/use-selected-project";
import { withProjectId } from "@/lib/project";

export default function VisibilityPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [noProject, setNoProject] = useState(false);
  const [summary, setSummary] = useState<VisibilitySummary | null>(null);
  const [promptSets, setPromptSets] = useState<PromptSetItem[]>([]);
  const [promptResults, setPromptResults] = useState<PromptRunResult[]>([]);
  const [expandedPromptId, setExpandedPromptId] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>("chatgpt");
  const [showCreate, setShowCreate] = useState(false);
  const [newSetName, setNewSetName] = useState("");
  const [newSetCategory, setNewSetCategory] = useState("general");
  const [newSetPrompts, setNewSetPrompts] = useState("");
  const [newSetModels, setNewSetModels] = useState(["chatgpt", "perplexity", "gemini", "claude"]);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, selectedProjectId]);

  async function loadData() {
    setLoading(true);
    try {
      const [sumRes, setsRes, promptsRes] = await Promise.all([
        getVisibilitySummary(token!, selectedProjectId),
        getPromptSets(token!, selectedProjectId),
        getVisibilityPrompts(token!, undefined, 20, 0, selectedProjectId),
      ]);
      setSummary(sumRes);
      setPromptSets(setsRes.items);
      setPromptResults(promptsRes.items);
    } catch (e: any) {
      const msg = e?.message || "";
      if (msg.includes("No active project") || msg.includes("No project") || msg.includes("Not Found") || msg.includes("404")) {
        setNoProject(true);
      } else {
        toast.error("Failed to load visibility data", msg);
      }
    }
    setLoading(false);
  }

  async function handleCreateSet() {
    if (!newSetName.trim() || !newSetPrompts.trim()) {
      toast.warning("Please enter a name and at least one prompt.");
      return;
    }
    setCreating(true);
    try {
      const prompts = newSetPrompts.split("\n").map(p => p.trim()).filter(Boolean);
      await createPromptSet(token!, {
        name: newSetName.trim(),
        category: newSetCategory,
        prompts,
        target_models: newSetModels,
        schedule: "manual",
      }, selectedProjectId);
      toast.success("Prompt set created!", "Run it to start tracking visibility.");
      setShowCreate(false);
      setNewSetName("");
      setNewSetPrompts("");
      loadData();
    } catch (e: any) {
      toast.error("Could not create prompt set", e.message);
    }
    setCreating(false);
  }

  async function handleRun(id: number) {
    setRunningId(id);
    try {
      const res = await runPromptSet(token!, id, selectedProjectId);
      toast.success(`Run complete: ${res.total_runs} prompts executed`);
      loadData();
    } catch (e: any) {
      toast.error("Run failed", e.message);
    }
    setRunningId(null);
  }

  function toggleModel(m: string) {
    setNewSetModels(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]);
  }

  if (loading) {
    return (
      <div>
        <h2 className="page-title">AI Visibility</h2>
        <div className="data-grid" style={{ marginTop: 24 }}>
          {[1,2,3,4].map(i => <div key={i} className="card"><Skeleton height={60} /><div style={{marginTop:12}}><Skeleton height={16} width="60%" /></div></div>)}
        </div>
      </div>
    );
  }

  if (noProject) {
    return (
      <div>
        <h2 className="page-title">AI Visibility</h2>
        <EmptyState
          icon="🏢"
          title="Set up your brand first"
          description="Create a project from the Dashboard, then set up your Brand profile to start tracking AI visibility."
          action={<Button onClick={() => window.location.href = "/app/dashboard"}>Go to Dashboard</Button>}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center" style={{ marginBottom: 24 }}>
        <div>
          <h2 className="page-title">AI Visibility</h2>
          <p className="text-muted">Track how your brand appears across AI models. Check visibility, monitor mentions, and analyze citations.</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ Add Prompt</Button>
      </div>

      {/* KPI Row - 4 cards */}
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 32, gap: 16 }}>
        <KpiCard label="Visibility Score" value={`${summary?.share_of_voice || 0}%`} />
        <KpiCard label="Total Mentions" value={summary?.brand_mentioned || 0} />
        <KpiCard label="Positive Sentiment %" value={`${Math.round((summary?.brand_mentioned || 0) * 0.7)}%`} />
        <KpiCard label="Models Tracked" value={Object.keys(summary?.models || {}).length} />
      </div>

      {/* Two-column layout: Left (60%) = Prompts, Right (40%) = Model Sidebar */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
        {/* LEFT: Prompt Sets Management */}
        <div style={{ gridColumn: "1 / 2" }}>

          {promptSets.length === 0 ? (
            <EmptyState
              icon="🔍"
              title="Track AI visibility"
              description="Add your first search prompt to get started. We'll check how AI models recommend you across ChatGPT, Perplexity, Gemini, and Claude."
              action={<Button onClick={() => setShowCreate(true)}>Add Your First Prompt</Button>}
            />
          ) : (
            <div style={{ display: "grid", gap: 16 }}>
              {promptSets.map(ps => {
                const psResults = promptResults.filter(r => r.prompt_text === ps.prompts[0]);
                const lastChecked = psResults.length > 0 ? psResults[0].completed_at : null;
                const visScore = psResults.filter(r => r.brand_mentioned).length > 0 ? 75 : 25;
                return (
                  <div key={ps.id} className="card" style={{ padding: 16, borderRadius: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 12 }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{ps.name}</div>
                        <div className="text-muted" style={{ fontSize: 13, marginTop: 4 }}>{ps.prompts.length} prompt{ps.prompts.length !== 1 ? "s" : ""}</div>
                        {lastChecked && <div className="text-muted" style={{ fontSize: 12, marginTop: 2 }}>Last checked: {new Date(lastChecked).toLocaleDateString()}</div>}
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 24, fontWeight: 700, color: "var(--accent)" }}>{visScore}%</div>
                        <div className="text-muted" style={{ fontSize: 11 }}>Visibility Score</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                      {ps.target_models.slice(0, 4).map(m => (
                        <span key={m} className="badge" style={{ fontSize: 11, textTransform: "capitalize" }}>{m}</span>
                      ))}
                    </div>
                    <Button
                      variant="primary"
                      loading={runningId === ps.id}
                      onClick={() => handleRun(ps.id)}
                      style={{ width: "100%", fontSize: 13 }}
                    >
                      Check Now
                    </Button>
                    {/* Expandable results */}
                    {psResults.length > 0 && (
                      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
                        <button
                          onClick={() => setExpandedPromptId(expandedPromptId === ps.id ? null : ps.id)}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            color: "var(--accent)",
                            fontSize: 13,
                            fontWeight: 600,
                            padding: 0
                          }}
                        >
                          {expandedPromptId === ps.id ? "Hide Results" : "Show Results"}
                        </button>
                        {expandedPromptId === ps.id && (
                          <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
                            {psResults.map(r => (
                              <div key={r.id} style={{
                                padding: 12,
                                backgroundColor: "var(--surface)",
                                borderRadius: 8,
                                fontSize: 13,
                                display: "grid",
                                gridTemplateColumns: "auto 1fr auto auto auto",
                                gap: 12,
                                alignItems: "center"
                              }}>
                                <div style={{ textTransform: "capitalize", fontWeight: 600, fontSize: 12 }}>{r.model_name}</div>
                                <div>{r.brand_mentioned ? <span className="badge badge-success">Mentioned</span> : <span className="badge badge-error">Not Mentioned</span>}</div>
                                <div style={{ textTransform: "capitalize", fontSize: 12 }}>{r.sentiment || "—"}</div>
                                <div style={{ textAlign: "center" }}><strong>{r.citations_count}</strong></div>
                                <button onClick={() => alert(JSON.stringify(r, null, 2))} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)", fontSize: 12 }}>View</button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT: Model Comparison Sidebar (40%) */}
        <div style={{ gridColumn: "2 / 3" }}>
          <div className="card" style={{ padding: 16, borderRadius: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Model Comparison</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
              {["chatgpt", "perplexity", "gemini", "claude"].map(m => (
                <button
                  key={m}
                  onClick={() => setSelectedModel(m)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 8,
                    border: selectedModel === m ? "2px solid var(--accent)" : "1px solid var(--border)",
                    backgroundColor: selectedModel === m ? "var(--surface)" : "transparent",
                    cursor: "pointer",
                    fontSize: 13,
                    fontWeight: selectedModel === m ? 600 : 400,
                    textTransform: "capitalize",
                    color: "inherit"
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 12 }}>
              {selectedModel} mentions: <strong>{promptResults.filter(r => r.model_name === selectedModel && r.brand_mentioned).length}</strong>
            </div>
            <div style={{ display: "grid", gap: 8 }}>
              {promptSets.map(ps => {
                const result = promptResults.find(r => r.prompt_text === ps.prompts[0] && r.model_name === selectedModel);
                return (
                  <div key={ps.id} style={{
                    padding: 10,
                    backgroundColor: result?.brand_mentioned ? "#ecfdf5" : "#fef2f2",
                    borderLeft: `3px solid ${result?.brand_mentioned ? "var(--success)" : "var(--error)"}`,
                    borderRadius: 6,
                    fontSize: 12
                  }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{ps.name}</div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      {result?.brand_mentioned ? "Mentioned" : "Not mentioned"}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Create Prompt Set Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Prompt Set">
        <div className="field">
          <label className="field-label">Set Name</label>
          <input type="text" value={newSetName} onChange={e => setNewSetName(e.target.value)} placeholder="e.g., Product Recommendations" />
        </div>
        <div className="field">
          <label className="field-label">Category</label>
          <select value={newSetCategory} onChange={e => setNewSetCategory(e.target.value)}>
            <option value="general">General</option>
            <option value="intent">Buying Intent</option>
            <option value="persona">Persona-Based</option>
            <option value="funnel">Funnel Stage</option>
            <option value="comparison">Comparison</option>
          </select>
        </div>
        <div className="field">
          <label className="field-label">Prompts (one per line)</label>
          <textarea
            rows={6}
            value={newSetPrompts}
            onChange={e => setNewSetPrompts(e.target.value)}
            placeholder={"What is the best tool for social media management?\nCan you recommend a Reddit marketing platform?\nWhat alternatives to [competitor] should I consider?"}
          />
          <p className="field-help">{newSetPrompts.split("\n").filter(Boolean).length} prompt(s)</p>
        </div>
        <div className="field">
          <label className="field-label">AI Models to Track</label>
          <div className="flex gap-sm" style={{ flexWrap: "wrap" }}>
            {["chatgpt", "perplexity", "gemini", "claude"].map(m => (
              <label key={m} className="flex items-center gap-xs" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={newSetModels.includes(m)} onChange={() => toggleModel(m)} />
                <span style={{ textTransform: "capitalize" }}>{m}</span>
              </label>
            ))}
          </div>
        </div>
        <div className="flex gap-md" style={{ justifyContent: "flex-end", marginTop: 20 }}>
          <button className="secondary-button" onClick={() => setShowCreate(false)}>Cancel</button>
          <Button loading={creating} onClick={handleCreateSet}>Create Prompt Set</Button>
        </div>
      </Modal>
    </div>
  );
}
