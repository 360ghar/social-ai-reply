"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";
import { apiRequest } from "@/lib/api";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { withProjectId } from "@/lib/project";
import {
  getVisibilitySummary, getPromptSets, createPromptSet, runPromptSet,
  getVisibilityPrompts, VisibilitySummary, PromptSetItem, PromptRunResult
} from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from "@/components/ui/dialog";
import { PageHeader } from "@/components/shared/page-header";
import { KPIGrid, type KPICardProps } from "@/components/shared/kpi-card";
import { EmptyState } from "@/components/shared/empty-state";
import { Search } from "lucide-react";

const AI_MODELS = ["chatgpt", "perplexity", "gemini", "claude"];

export default function VisibilityPage() {
  const { token } = useAuth();
  const { success, error, warning } = useToast();
  const router = useRouter();
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
  const [newSetModels, setNewSetModels] = useState<string[]>([...AI_MODELS]);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [inspectedRun, setInspectedRun] = useState<PromptRunResult | null>(null);

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
    } catch (e: unknown) {
      const msg = getErrorMessage(e) || "";
      if (msg.includes("No active project") || msg.includes("No project") || msg.includes("Not Found") || msg.includes("404")) {
        setNoProject(true);
      } else {
        error("Failed to load visibility data", msg);
      }
    }
    setLoading(false);
  }

  async function handleCreateSet() {
    if (!newSetName.trim() || !newSetPrompts.trim()) {
      warning("Please enter a name and at least one prompt.");
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
      success("Prompt set created!", "Run it to start tracking visibility.");
      setShowCreate(false);
      setNewSetName("");
      setNewSetPrompts("");
      loadData();
    } catch (e: unknown) {
      error("Could not create prompt set", getErrorMessage(e));
    }
    setCreating(false);
  }

  async function handleRun(id: number) {
    setRunningId(id);
    try {
      const res = await runPromptSet(token!, id, selectedProjectId);
      success(`Run complete: ${res.total_runs} prompts executed`);
      loadData();
    } catch (e: unknown) {
      error("Run failed", getErrorMessage(e));
    }
    setRunningId(null);
  }

  function toggleModel(m: string) {
    setNewSetModels(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]);
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader title="AI Visibility" description="Track how your brand appears across AI models." />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[1,2,3].map(i => (
            <Card key={i} className="p-4">
              <Skeleton className="h-[60px] w-full" />
              <Skeleton className="h-4 w-3/5 mt-3" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (noProject) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader title="AI Visibility" description="Track how your brand appears across AI models." />
        <EmptyState
          title="Set up your brand first"
          description="Create a project from the Dashboard, then set up your Brand profile to start tracking AI visibility."
          action={{ label: "Go to Dashboard", onClick: () => router.push("/app/dashboard") }}
        />
      </div>
    );
  }

  // KPI cards
  const kpiCards: KPICardProps[] = [
    { label: "Visibility Score", value: `${summary?.share_of_voice || 0}%` },
    { label: "Total Mentions", value: summary?.brand_mentioned || 0 },
    { label: "Models Tracked", value: Object.keys(summary?.models || {}).length },
  ];

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        title="AI Visibility"
        description="Track how your brand appears across AI models. Check visibility, monitor mentions, and analyze citations."
        actions={
          <Button onClick={() => setShowCreate(true)}>+ Add Prompt Set</Button>
        }
      />

      {/* KPI Row - 3 cards */}
      <KPIGrid cards={kpiCards} columns={3} className="grid-cols-1 sm:grid-cols-3" />

      {/* Two-column layout: Left = Prompts, Right = Model Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LEFT: Prompt Sets Management */}
        <div>
          {promptSets.length === 0 ? (
            <EmptyState
              icon={Search}
              title="Track AI visibility"
              description="Add your first search prompt to get started. We'll check how AI models recommend you across ChatGPT, Perplexity, Gemini, and Claude."
              action={{ label: "Add Your First Prompt", onClick: () => setShowCreate(true) }}
            />
          ) : (
            <div className="space-y-4">
              {promptSets.map(ps => {
                const psResults = promptResults.filter(r => ps.prompts.includes(r.prompt_text));
                const lastChecked = psResults.length > 0 ? psResults[0].completed_at : null;
                const visScore = psResults.filter(r => r.brand_mentioned).length > 0 ? 75 : 25;
                return (
                  <Card key={ps.id} className="p-5 rounded-xl">
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <div className="text-sm font-semibold">{ps.name}</div>
                        <div className="text-sm text-muted-foreground mt-1">{ps.prompts.length} prompt{ps.prompts.length !== 1 ? "s" : ""}</div>
                        {lastChecked && <div className="text-xs text-muted-foreground mt-0.5">Last checked: {new Date(lastChecked).toLocaleDateString()}</div>}
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-primary">{visScore}%</div>
                        <div className="text-xs text-muted-foreground">Visibility Score</div>
                      </div>
                    </div>
                    <div className="flex gap-2 mb-3">
                      {ps.target_models.slice(0, 4).map(m => (
                        <Badge key={m} variant="secondary" className="text-xs capitalize">{m}</Badge>
                      ))}
                    </div>
                    <Button
                      className="w-full text-sm"
                      disabled={runningId === ps.id}
                      onClick={() => handleRun(ps.id)}
                    >
                      {runningId === ps.id && <Loader2 className="h-4 w-4 animate-spin" />}
                      Check Now
                    </Button>
                    {/* Expandable results */}
                    {psResults.length > 0 && (
                      <div className="mt-3 pt-3 border-t">
                        <button
                          onClick={() => setExpandedPromptId(expandedPromptId === ps.id ? null : ps.id)}
                          className="bg-transparent border-none cursor-pointer text-primary text-sm font-semibold p-0"
                        >
                          {expandedPromptId === ps.id ? "Hide Results" : "Show Results"}
                        </button>
                        {expandedPromptId === ps.id && (
                          <div className="mt-3 space-y-2">
                            {psResults.map(r => (
                              <div key={r.id} className="p-4 bg-muted rounded-xl text-sm grid grid-cols-[auto_1fr_auto_auto_auto] gap-3 items-center">
                                <div className="capitalize font-semibold text-xs">{r.model_name}</div>
                                <div>
                                  {r.brand_mentioned
                                    ? <span className="inline-flex items-center justify-center rounded-full border border-success/20 bg-success/10 px-2 py-0.5 text-xs font-semibold text-success">Mentioned</span>
                                    : <span className="inline-flex items-center justify-center rounded-full border border-destructive/20 bg-destructive/10 px-2 py-0.5 text-xs font-semibold text-destructive">Not Mentioned</span>
                                  }
                                </div>
                                <div className="capitalize text-xs">{r.sentiment || "—"}</div>
                                <div className="text-center"><strong>{r.citations_count}</strong></div>
                                <button
                                  onClick={() => setInspectedRun(r)}
                                  className="bg-transparent border-none cursor-pointer text-primary text-xs"
                                >
                                  View
                                </button>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT: Model Comparison Sidebar */}
        <div>
          <Card className="p-5 rounded-xl">
            <div className="text-sm font-semibold mb-3">Model Comparison</div>
            <div className="flex flex-col gap-2 mb-4">
              {AI_MODELS.map(m => (
                <button
                  key={m}
                  onClick={() => setSelectedModel(m)}
                  className={`px-3 py-2.5 rounded-lg border text-sm capitalize cursor-pointer ${
                    selectedModel === m
                      ? "border-primary border-2 bg-muted font-semibold"
                      : "border-border bg-transparent font-normal"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <div className="text-xs text-muted-foreground mb-3">
              {selectedModel} mentions: <strong>{promptResults.filter(r => r.model_name === selectedModel && r.brand_mentioned).length}</strong>
            </div>
            <div className="space-y-2">
              {promptSets.map(ps => {
                const result = promptResults.find(r => ps.prompts.includes(r.prompt_text) && r.model_name === selectedModel);
                return (
                  <div key={ps.id} className={`p-2.5 rounded-md text-xs ${
                    result?.brand_mentioned
                      ? "bg-success/10 border-l-[3px] border-l-success text-success"
                      : "bg-destructive/10 border-l-[3px] border-l-destructive text-destructive"
                  }`}>
                    <div className="font-semibold mb-1">{ps.name}</div>
                    <div className="text-xs opacity-80">
                      {result?.brand_mentioned ? "Mentioned" : "Not mentioned"}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>

      {/* Run Detail Dialog */}
      <Dialog open={inspectedRun !== null} onOpenChange={(open) => { if (!open) setInspectedRun(null); }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Run Detail</DialogTitle>
            <DialogDescription>Full result data for this prompt run.</DialogDescription>
          </DialogHeader>
          <pre className="overflow-auto rounded-md bg-muted p-4 text-xs max-h-96">
            {JSON.stringify(inspectedRun, null, 2)}
          </pre>
        </DialogContent>
      </Dialog>

      {/* Create Prompt Set Modal */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Prompt Set</DialogTitle>
            <DialogDescription>Add a new set of prompts to track your AI visibility.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Set Name</Label>
              <Input
                type="text"
                value={newSetName}
                onChange={e => setNewSetName(e.target.value)}
                placeholder="e.g., Product Recommendations"
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={newSetCategory} onValueChange={(v) => setNewSetCategory(v ?? "general")}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="intent">Buying Intent</SelectItem>
                  <SelectItem value="persona">Persona-Based</SelectItem>
                  <SelectItem value="funnel">Funnel Stage</SelectItem>
                  <SelectItem value="comparison">Comparison</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Prompts (one per line)</Label>
              <Textarea
                rows={6}
                value={newSetPrompts}
                onChange={e => setNewSetPrompts(e.target.value)}
                placeholder={"What is the best tool for social media management?\nCan you recommend a Reddit marketing platform?\nWhat alternatives to [competitor] should I consider?"}
              />
              <p className="text-xs text-muted-foreground">{newSetPrompts.split("\n").filter(Boolean).length} prompt(s)</p>
            </div>
            <div className="space-y-2">
              <Label>AI Models to Track</Label>
              <div className="flex flex-wrap gap-3">
                {AI_MODELS.map(m => (
                  <label key={m} className="flex items-center gap-1.5 cursor-pointer">
                    <input type="checkbox" checked={newSetModels.includes(m)} onChange={() => toggleModel(m)} />
                    <span className="capitalize text-sm">{m}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button disabled={creating} onClick={handleCreateSet}>
              {creating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Prompt Set
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
