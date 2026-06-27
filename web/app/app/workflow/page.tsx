"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Zap, CheckCircle2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { useWorkflowStore, STEP_ORDER, STEP_META, type StepId } from "@/stores/workflow-store";
import { WorkflowNode } from "@/components/workflow/workflow-node";
import { PipelineTerminal } from "@/components/workflow/pipeline-terminal";
import { StepCompany } from "@/components/workflow/steps/step-company";
import { StepBrand } from "@/components/workflow/steps/step-brand";
import { StepPersonas } from "@/components/workflow/steps/step-personas";
import { StepCommunities } from "@/components/workflow/steps/step-communities";
import { StepCompetitors } from "@/components/workflow/steps/step-competitors";
import { StepLaunch } from "@/components/workflow/steps/step-launch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function WorkflowPage() {
  const { token } = useAuth();
  const router = useRouter();
  const selectedProjectId = useSelectedProjectId();

  const { activeStep, statuses, toggleStep, openStep, setStatus } = useWorkflowStore();

  const [summaries, setSummaries] = useState<Record<StepId, string>>({
    company:     "Not configured",
    brand:       "No keywords",
    personas:    "None yet",
    communities: "None yet",
    competitors: "No data yet",
    launch:      "Ready to scan",
  });

  // Zero-input enrichment
  const [enrichUrl, setEnrichUrl] = useState("");
  const [terminalActive, setTerminalActive] = useState(false);
  const [terminalEndpoint, setTerminalEndpoint] = useState("");

  const updateSummary = useCallback((id: StepId, summary: string) => {
    setSummaries((prev) => ({ ...prev, [id]: summary }));
  }, []);

  function advanceTo(id: StepId) {
    const idx = STEP_ORDER.indexOf(id);
    const next = STEP_ORDER[idx + 1];
    if (next) openStep(next);
  }

  const readiness = [
    { label: "Company Setup",   ok: statuses.company     !== "empty", href: "#" },
    { label: "Brand Keywords",  ok: statuses.brand        !== "empty", href: "#" },
    { label: "Personas",        ok: statuses.personas     !== "empty", href: "#" },
    { label: "Communities",     ok: statuses.communities  !== "empty", href: "#" },
    { label: "Competitor Intel",ok: statuses.competitors !== "empty", href: "#" },
  ];
  const doneCount = readiness.filter((r) => r.ok).length;

  function startEnrichment() {
    if (!enrichUrl.trim() || !token) return;
    let url = enrichUrl.trim();
    if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
    const endpoint = `${API_BASE}/v1/analyze/stream?url=${encodeURIComponent(url)}`;
    setTerminalEndpoint(endpoint);
    setTerminalActive(true);
  }

  function handleTerminalComplete(data: Record<string, unknown>) {
    // Auto-update summaries from enrichment results
    if (data.name) {
      const nameStr = String(data.name);
      const urlStr = data.website_url ? ` · ${String(data.website_url)}` : "";
      updateSummary("company", `${nameStr}${urlStr}`);
      setStatus("company", "done");
    }
    const comps = data.competitors as string[] | undefined;
    if (comps && comps.length > 0) {
      updateSummary("competitors", `${comps.length} competitors found`);
      setStatus("competitors", "partial");
    }
    // Open next incomplete step
    const nextEmpty = STEP_ORDER.find((id) => statuses[id] === "empty");
    if (nextEmpty) openStep(nextEmpty);
  }

  function handleTerminalData(key: string, value: unknown) {
    if (key === "keywords_count" && Number(value) > 0) {
      updateSummary("brand", `${value} keywords`);
      setStatus("brand", "done");
    }
    if (key === "personas_count" && Number(value) > 0) {
      updateSummary("personas", `${value} personas`);
      setStatus("personas", "done");
    }
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pipeline Setup</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Drop a URL to auto-analyze your brand, or configure each step manually below.
        </p>
      </div>

      {/* Zero-input enrichment */}
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <Zap className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-semibold">Auto-Analyze URL</p>
              <p className="text-xs text-muted-foreground">
                Paste your product URL — we crawl it, extract brand intelligence, generate keywords and personas automatically
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Input
              value={enrichUrl}
              onChange={(e) => setEnrichUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && startEnrichment()}
              placeholder="https://yourproduct.com"
              className="flex-1 h-10"
              disabled={terminalActive}
            />
            <Button
              onClick={startEnrichment}
              disabled={terminalActive || !enrichUrl.trim()}
              className="shrink-0"
            >
              <Zap className="h-3.5 w-3.5 mr-1" />
              Analyze
            </Button>
          </div>

          {/* Pipeline health dots */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              {readiness.map((item) => (
                <div
                  key={item.label}
                  title={`${item.label}: ${item.ok ? "configured" : "not set up"}`}
                  className={cn(
                    "h-1.5 w-8 rounded-full transition-colors",
                    item.ok ? "bg-primary" : "bg-muted"
                  )}
                />
              ))}
            </div>
            <span className="text-xs text-muted-foreground">
              {doneCount}/{readiness.length} configured
              {doneCount === readiness.length && (
                <span className="ml-1.5 text-primary inline-flex items-center gap-0.5">
                  <CheckCircle2 className="h-3 w-3" /> Ready
                </span>
              )}
            </span>
          </div>
        </div>

        {/* Terminal — renders below the input when active */}
        {terminalActive && (
          <PipelineTerminal
            endpointUrl={terminalEndpoint}
            token={token}
            active={terminalActive}
            onComplete={handleTerminalComplete}
            onData={handleTerminalData}
            onClose={() => setTerminalActive(false)}
            className="rounded-none border-0 border-t"
          />
        )}
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-border" />
        <span className="text-xs text-muted-foreground uppercase tracking-wider">or configure step by step</span>
        <div className="flex-1 h-px bg-border" />
      </div>

      {/* Step-by-step tree */}
      <div>
        {STEP_ORDER.map((stepId, index) => {
          const meta = STEP_META[stepId];
          const status = statuses[stepId];
          const summary = summaries[stepId];

          return (
            <WorkflowNode
              key={stepId}
              stepId={stepId}
              index={index}
              label={meta.label}
              description={meta.description}
              status={status}
              isActive={activeStep === stepId}
              isLast={index === STEP_ORDER.length - 1}
              onToggle={() => toggleStep(stepId)}
              summary={<span className="text-xs">{summary}</span>}
            >
              {stepId === "company" && (
                <StepCompany
                  token={token}
                  onStatusChange={(s) => setStatus("company", s)}
                  onSummary={(s) => updateSummary("company", s)}
                  onContinue={() => advanceTo("company")}
                />
              )}
              {stepId === "brand" && (
                <StepBrand
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("brand", s)}
                  onSummary={(s) => updateSummary("brand", s)}
                  onContinue={() => advanceTo("brand")}
                />
              )}
              {stepId === "personas" && (
                <StepPersonas
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("personas", s)}
                  onSummary={(s) => updateSummary("personas", s)}
                  onContinue={() => advanceTo("personas")}
                />
              )}
              {stepId === "communities" && (
                <StepCommunities
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("communities", s)}
                  onSummary={(s) => updateSummary("communities", s)}
                  onContinue={() => advanceTo("communities")}
                />
              )}
              {stepId === "competitors" && (
                <StepCompetitors
                  token={token}
                  projectId={selectedProjectId}
                  onStatusChange={(s) => setStatus("competitors", s)}
                  onContinue={() => advanceTo("competitors")}
                />
              )}
              {stepId === "launch" && (
                <StepLaunch
                  token={token}
                  projectId={selectedProjectId}
                  readiness={readiness}
                  onStatusChange={(s) => {
                    setStatus("launch", s);
                    if (s === "done") updateSummary("launch", "Scan complete");
                  }}
                />
              )}
            </WorkflowNode>
          );
        })}
      </div>
    </div>
  );
}
