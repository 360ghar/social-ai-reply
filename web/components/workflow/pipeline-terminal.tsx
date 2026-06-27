"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Loader2, CheckCircle2, AlertTriangle, X, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type TerminalEvent =
  | { type: "log"; msg: string; level?: "info" | "success" | "warn" | "error" }
  | { type: "section"; label: string }
  | { type: "data"; key: string; value: unknown }
  | { type: "complete"; company?: Record<string, unknown> }
  | { type: "error"; msg: string };

interface TerminalLine {
  id: number;
  kind: "log" | "section" | "error";
  text: string;
  level?: string;
}

interface PipelineTerminalProps {
  /** Full URL for the SSE endpoint, including auth header is handled via token prop */
  endpointUrl: string;
  /** Bearer token — sent as a query param since EventSource doesn't support headers */
  token: string;
  /** Called when a "complete" event arrives */
  onComplete?: (data: Record<string, unknown>) => void;
  /** Called when each "data" key-value pair arrives (for auto-populating form state) */
  onData?: (key: string, value: unknown) => void;
  /** Whether the terminal is visible */
  active: boolean;
  /** Called to close/dismiss the terminal */
  onClose?: () => void;
  className?: string;
}

let _lineId = 0;
const nextId = () => ++_lineId;

const LEVEL_COLOR: Record<string, string> = {
  info:    "text-green-400",
  success: "text-emerald-300",
  warn:    "text-yellow-400",
  error:   "text-red-400",
};

export function PipelineTerminal({
  endpointUrl,
  token,
  onComplete,
  onData,
  active,
  onClose,
  className,
}: PipelineTerminalProps) {
  const [lines, setLines] = useState<TerminalLine[]>([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const sourceRef = useRef<EventSource | null>(null);

  const push = useCallback((line: TerminalLine) => {
    setLines((prev) => [...prev.slice(-199), line]); // cap at 200 lines
  }, []);

  useEffect(() => {
    if (!active || !endpointUrl || !token) return;

    // Cleanup previous connection
    if (sourceRef.current) {
      sourceRef.current.close();
    }

    setLines([]);
    setRunning(true);
    setDone(false);
    setError(null);

    // EventSource doesn't support Authorization headers, so pass token as query param.
    // The backend must accept ?token= as an alternative to the Bearer header.
    const url = `${endpointUrl}&token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    sourceRef.current = es;

    es.onmessage = (evt) => {
      try {
        const data: TerminalEvent = JSON.parse(evt.data);

        if (data.type === "log") {
          push({ id: nextId(), kind: "log", text: data.msg, level: data.level ?? "info" });
        } else if (data.type === "section") {
          push({ id: nextId(), kind: "section", text: data.label });
        } else if (data.type === "data") {
          onData?.(data.key, data.value);
        } else if (data.type === "complete") {
          push({ id: nextId(), kind: "log", text: "Pipeline complete ✓", level: "success" });
          setRunning(false);
          setDone(true);
          if (data.company) onComplete?.(data.company as Record<string, unknown>);
          es.close();
        } else if (data.type === "error") {
          push({ id: nextId(), kind: "error", text: data.msg });
          setError(data.msg);
          setRunning(false);
          es.close();
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      setRunning(false);
      if (!done) {
        push({ id: nextId(), kind: "error", text: "Connection lost — check backend logs" });
        setError("Stream disconnected");
      }
      es.close();
    };

    return () => {
      es.close();
    };
  }, [active, endpointUrl, token]);

  // Auto-scroll to bottom as lines arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  if (!active) return null;

  return (
    <div
      className={cn(
        "rounded-xl border border-border/50 bg-[#0a0a0a] overflow-hidden flex flex-col",
        "shadow-lg shadow-black/30",
        className,
      )}
    >
      {/* Terminal titlebar */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 bg-[#111] shrink-0">
        <div className="flex gap-1.5">
          <div className="h-3 w-3 rounded-full bg-[#ff5f57]" />
          <div className="h-3 w-3 rounded-full bg-[#febc2e]" />
          <div className="h-3 w-3 rounded-full bg-[#28c840]" />
        </div>
        <span className="flex-1 text-center text-xs text-white/30 font-mono select-none">
          RedditFlow Pipeline — Running Analysis
        </span>
        <div className="flex items-center gap-2">
          {running && (
            <Loader2 className="h-3 w-3 text-green-400 animate-spin" />
          )}
          {done && !error && (
            <CheckCircle2 className="h-3 w-3 text-emerald-400" />
          )}
          {error && (
            <AlertTriangle className="h-3 w-3 text-yellow-400" />
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-white/30 hover:text-white/70 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Log lines */}
      <div className="flex-1 overflow-y-auto px-4 py-3 font-mono text-xs leading-5 space-y-0.5 min-h-[220px] max-h-[380px]">
        {lines.length === 0 && running && (
          <div className="text-white/20 animate-pulse">Connecting…</div>
        )}

        {lines.map((line) => {
          if (line.kind === "section") {
            return (
              <div key={line.id} className="flex items-center gap-2 mt-3 mb-1">
                <div className="h-px flex-1 bg-white/5" />
                <span className="text-white/30 text-[10px] uppercase tracking-widest px-1">
                  {line.text}
                </span>
                <div className="h-px flex-1 bg-white/5" />
              </div>
            );
          }
          if (line.kind === "error") {
            return (
              <div key={line.id} className="flex gap-2 text-red-400">
                <span className="text-red-600 shrink-0">✗</span>
                <span>{line.text}</span>
              </div>
            );
          }
          const colorClass = LEVEL_COLOR[line.level ?? "info"] ?? LEVEL_COLOR.info;
          return (
            <div key={line.id} className="flex gap-2">
              <span className="text-white/20 shrink-0 select-none">&gt;</span>
              <span className={cn("flex-1 break-all", colorClass)}>{line.text}</span>
            </div>
          );
        })}

        {/* Blinking cursor */}
        {running && (
          <div className="flex gap-2">
            <span className="text-white/20 select-none">&gt;</span>
            <span className="inline-block w-2 h-3.5 bg-green-400 animate-pulse" />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Status bar */}
      <div className="shrink-0 border-t border-white/5 bg-[#111] px-4 py-1.5 flex items-center justify-between">
        <span className="text-[10px] font-mono text-white/25">
          {lines.filter((l) => l.kind === "log").length} events
        </span>
        {done && !error && (
          <span className="text-[10px] font-mono text-emerald-400">
            ✓ Complete — scroll up to review
          </span>
        )}
        {error && (
          <span className="text-[10px] font-mono text-yellow-400">
            ⚠ {error}
          </span>
        )}
        {running && (
          <span className="text-[10px] font-mono text-green-400 animate-pulse">
            ● live
          </span>
        )}
      </div>
    </div>
  );
}
