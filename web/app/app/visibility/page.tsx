"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, EmptyState, KpiCard, Spinner, Tabs, Skeleton } from "@/components/ui";
import { Modal } from "@/components/modal";
import {
  getVisibilitySummary, getPromptSets, createPromptSet, runPromptSet,
  getVisibilityPrompts, VisibilitySummary, PromptSetItem, PromptRunResult
} from "@/lib/api";
import { useSelectedProjectId } from "@/lib/use-selected-project";

export default function VisibilityPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [noProject, setNoProject] = useState(false);
  const [summary, setSummary] = useState<VisibilitySummary | null>(null);
  const [promptSets, setPromptSets] = useState<PromptSetItem[]>([]);
  const [promptResults, setPromptResults] = useState<PromptRunResult[]>([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [showCreate, setShowCreate] = useState(false);
  const [newSetName, setNewSetName] = useState("");
  const [newSetCategory, setNewSetCategory] = useState("general");
  const [newSetPrompts, setNewSetPrompts] = useState("");
  const [newSetModels, setNewSetModels] = useState(["chatgpt", "perplexity", "gemini", "claude"]);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [modelFilter, setModelFilter] = useState("");

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
          <p className="text-muted">Track how AI models recommend your brand across ChatGPT, Perplexity, Gemini, and Claude.</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>+ New Prompt Set</Button>
      </div>

      {/* KPI Row */}
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 32 }}>
        <KpiCard label="Share of Voice" value={`${summary?.share_of_voice || 0}%`} />
        <KpiCard label="Brand Mentioned" value={summary?.brand_mentioned || 0} />
        <KpiCard label="Total Prompt Runs" value={summary?.total_runs || 0} />
        <KpiCard label="Citations Found" value={summary?.total_citations || 0} />
      </div>

      {/* Model Breakdown */}
      {summary && summary.total_runs > 0 && (
        <div className="card" style={{ marginBottom: 32 }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Share of Voice by Model</h3>
          <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
            {Object.entries(summary.models).map(([model, data]) => (
              <div key={model} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: "var(--accent)" }}>{data.share_of_voice}%</div>
                <div className="text-muted" style={{ textTransform: "capitalize", marginTop: 4 }}>{model}</div>
                <div className="text-muted" style={{ fontSize: 12 }}>{data.brand_mentioned}/{data.total_runs} prompts</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Tabs
        tabs={[
          { key: "overview", label: "Prompt Sets" },
          { key: "results", label: "Run Results", count: promptResults.length },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === "overview" && (
        <div style={{ marginTop: 20 }}>
          {promptSets.length === 0 ? (
            <EmptyState
              icon="🎯"
              title="No prompt sets yet"
              description="Create a prompt set with questions your customers ask AI. We'll track whether AI recommends your brand."
              action={<Button onClick={() => setShowCreate(true)}>Create Your First Prompt Set</Button>}
            />
          ) : (
            <div className="item-list">
              {promptSets.map(ps => (
                <div key={ps.id} className="list-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <strong>{ps.name}</strong>
                    <span className="badge" style={{ marginLeft: 8 }}>{ps.category}</span>
                    <div className="text-muted" style={{ marginTop: 4 }}>
                      {ps.prompts.length} prompt{ps.prompts.length !== 1 ? "s" : ""} · Models: {ps.target_models.join(", ")}
                    </div>
                  </div>
                  <div className="flex gap-sm">
                    <Button
                      variant="primary"
                      loading={runningId === ps.id}
                      onClick={() => handleRun(ps.id)}
                    >
                      Run Now
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "results" && (
        <div style={{ marginTop: 20 }}>
          <div style={{ marginBottom: 16 }}>
            <select value={modelFilter} onChange={e => setModelFilter(e.target.value)} style={{ minWidth: 160 }}>
              <option value="">All Models</option>
              <option value="chatgpt">ChatGPT</option>
              <option value="perplexity">Perplexity</option>
              <option value="gemini">Gemini</option>
              <option value="claude">Claude</option>
            </select>
          </div>
          {promptResults.length === 0 ? (
            <EmptyState icon="📊" title="No results yet" description="Run a prompt set to see how AI models respond." />
          ) : (
            <div className="table-list">
              <table style={{ width: "100%" }}>
                <thead>
                  <tr>
                    <th>Prompt</th>
                    <th>Model</th>
                    <th>Brand Found</th>
                    <th>Sentiment</th>
                    <th>Citations</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {promptResults
                    .filter(r => !modelFilter || r.model_name === modelFilter)
                    .map(r => (
                    <tr key={r.id}>
                      <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.prompt_text}</td>
                      <td style={{ textTransform: "capitalize" }}>{r.model_name}</td>
                      <td>{r.brand_mentioned ? <span className="badge badge-success">Yes</span> : <span className="badge badge-error">No</span>}</td>
                      <td style={{ textTransform: "capitalize" }}>{r.sentiment || "—"}</td>
                      <td>{r.citations_count}</td>
                      <td><span className={`badge badge-${r.status === "complete" ? "success" : r.status === "failed" ? "error" : "info"}`}>{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

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
