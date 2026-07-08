"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Loader2,
  Sparkles,
} from "lucide-react";

import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { PlatformIcon } from "@/components/shared/platform-icon";
import { StatusBadge } from "@/components/shared/status-badge";
import { SheetPanel } from "@/components/shared/sheet-panel";
import { cn } from "@/lib/utils";
import {
  listSuggestions,
  generateSuggestions,
  approveSuggestion,
  rejectSuggestion,
  type TweetSuggestion,
  type SuggestionPlatform,
  type SuggestionStatus,
} from "@/lib/api/tweet-suggestions";

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const PLATFORM_TABS = [
  { id: "all" as const, label: "All", icon: null },
  { id: "x" as const, label: "X", icon: "x" as const },
  { id: "instagram" as const, label: "Instagram", icon: "instagram" as const },
  { id: "linkedin" as const, label: "LinkedIn", icon: "linkedin" as const },
];

const STATUS_VARIANT: Record<SuggestionStatus, "success" | "warning" | "error" | "info" | "neutral" | "primary"> = {
  pending: "warning",
  approved: "info",
  rejected: "error",
  published: "success",
};

function formatDateKey(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

function buildMonthGrid(year: number, month: number): Date[][] {
  const firstDay = new Date(year, month, 1);
  const startDow = firstDay.getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevMonthDays = new Date(year, month, 0).getDate();

  const weeks: Date[][] = [];
  let week: Date[] = [];

  for (let i = startDow - 1; i >= 0; i--) {
    week.push(new Date(year, month - 1, prevMonthDays - i));
  }
  for (let day = 1; day <= daysInMonth; day++) {
    week.push(new Date(year, month, day));
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length > 0) {
    const remaining = 7 - week.length;
    for (let day = 1; day <= remaining; day++) {
      week.push(new Date(year, month + 1, day));
    }
    weeks.push(week);
  }
  return weeks;
}

function buildWeekGrid(weekStart: Date): Date[] {
  const days: Date[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    days.push(d);
  }
  return days;
}

function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  return d;
}

function getMonthYear(date: Date): { year: number; month: number } {
  return { year: date.getFullYear(), month: date.getMonth() };
}

interface ContentCalendarProps {
  token: string | null;
}

export function ContentCalendar({ token }: ContentCalendarProps) {
  const { success, error: toastError } = useToast();

  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState<"month" | "week">("month");
  const [platformFilter, setPlatformFilter] = useState<string>("all");

  const [suggestions, setSuggestions] = useState<TweetSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [operatingId, setOperatingId] = useState<number | null>(null);

  const [selectedSuggestion, setSelectedSuggestion] = useState<TweetSuggestion | null>(null);

  const [showGenerate, setShowGenerate] = useState(false);
  const [genDayCount, setGenDayCount] = useState(7);
  const [genPlatforms, setGenPlatforms] = useState<SuggestionPlatform[]>(["x", "instagram", "linkedin"]);
  const [generating, setGenerating] = useState(false);

  const { year, month } = getMonthYear(currentDate);
  const weekStart = getWeekStart(currentDate);

  const gridDays = useMemo(
    () =>
      viewMode === "month"
        ? buildMonthGrid(year, month)
        : [buildWeekGrid(weekStart)],
    [viewMode, year, month, weekStart],
  );

  const fetchSuggestions = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const firstDay = gridDays[0][0];
      const lastDay = gridDays[gridDays.length - 1][6];
      const data = await listSuggestions(token, {
        date_from: formatDateKey(firstDay),
        date_to: formatDateKey(lastDay),
      });
      setSuggestions(data);
    } catch {
      setSuggestions([]);
    }
    setLoading(false);
  }, [token, gridDays]);

  useEffect(() => {
    void fetchSuggestions();
  }, [fetchSuggestions]);

  const suggestionsByDate = useMemo(() => {
    const map = new Map<string, TweetSuggestion[]>();
    for (const s of suggestions) {
      const key = s.suggested_for_date.split("T")[0];
      const existing = map.get(key) ?? [];
      existing.push(s);
      map.set(key, existing);
    }
    return map;
  }, [suggestions]);

  const daySuggestions = useCallback(
    (date: Date): TweetSuggestion[] => {
      const key = formatDateKey(date);
      const items = suggestionsByDate.get(key) ?? [];
      if (platformFilter === "all") return items;
      return items.filter((s) => s.platform === platformFilter);
    },
    [suggestionsByDate, platformFilter],
  );

  function navigate(delta: number) {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      if (viewMode === "month") {
        d.setMonth(d.getMonth() + delta);
      } else {
        d.setDate(d.getDate() + delta * 7);
      }
      return d;
    });
  }

  function goToday() {
    setCurrentDate(new Date());
  }

  async function handleGenerate() {
    if (!token) return;
    setGenerating(true);
    try {
      const result = await generateSuggestions(token, {
        day_count: genDayCount,
        platforms: genPlatforms.length > 0 ? genPlatforms : undefined,
      });
      success(`Generated ${result.generated} suggestions`);
      setShowGenerate(false);
      await fetchSuggestions();
    } catch (err: unknown) {
      toastError("Failed to generate suggestions", getErrorMessage(err));
    }
    setGenerating(false);
  }

  function toggleGenPlatform(platform: SuggestionPlatform) {
    setGenPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform],
    );
  }

  async function handleApprove(suggestion: TweetSuggestion) {
    if (!token) return;
    setOperatingId(suggestion.id);
    try {
      await approveSuggestion(token, suggestion.id);
      success("Suggestion approved");
      setSuggestions((prev) =>
        prev.map((s) =>
          s.id === suggestion.id ? { ...s, status: "approved" as const } : s,
        ),
      );
      setSelectedSuggestion((prev) =>
        prev?.id === suggestion.id
          ? { ...prev, status: "approved" as const }
          : prev,
      );
    } catch (err: unknown) {
      toastError("Failed to approve", getErrorMessage(err));
    }
    setOperatingId(null);
  }

  async function handleReject(suggestion: TweetSuggestion) {
    if (!token) return;
    setOperatingId(suggestion.id);
    try {
      await rejectSuggestion(token, suggestion.id);
      success("Suggestion rejected");
      setSuggestions((prev) =>
        prev.map((s) =>
          s.id === suggestion.id ? { ...s, status: "rejected" as const } : s,
        ),
      );
      setSelectedSuggestion((prev) =>
        prev?.id === suggestion.id
          ? { ...prev, status: "rejected" as const }
          : prev,
      );
    } catch (err: unknown) {
      toastError("Failed to reject", getErrorMessage(err));
    }
    setOperatingId(null);
  }

  const viewLabel =
    viewMode === "month"
      ? currentDate.toLocaleDateString("en-US", { month: "long", year: "numeric" })
      : `${weekStart.toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${
          new Date(weekStart.getTime() + 6 * 86400000).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        }`;

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <button
            type="button"
            onClick={goToday}
            className="text-sm font-semibold hover:text-primary min-w-[180px] text-center cursor-pointer bg-transparent border-none"
          >
            {viewLabel}
          </button>
          <Button variant="outline" size="sm" onClick={() => navigate(1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="xs" onClick={goToday}>
            Today
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-lg bg-muted/50 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("month")}
              className={cn(
                "px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer",
                viewMode === "month"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              Month
            </button>
            <button
              type="button"
              onClick={() => setViewMode("week")}
              className={cn(
                "px-2.5 py-1 text-xs font-medium rounded-md transition-all cursor-pointer",
                viewMode === "week"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              Week
            </button>
          </div>
          <Button size="sm" onClick={() => setShowGenerate(true)}>
            <Sparkles className="h-4 w-4" />
            Generate Suggestions
          </Button>
        </div>
      </div>

      {/* Platform filter tabs */}
      <div className="flex items-center gap-1 rounded-lg bg-muted/50 p-1 w-fit">
        {PLATFORM_TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setPlatformFilter(tab.id)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all cursor-pointer",
              platformFilter === tab.id
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-background/50",
            )}
          >
            {tab.icon && (
              <PlatformIcon
                platform={tab.icon}
                className="[&_svg]:h-3.5 [&_svg]:w-3.5"
              />
            )}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Calendar grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="rounded-lg border border-border overflow-hidden">
          {/* Day headers */}
          <div className="grid grid-cols-7 bg-muted/30 border-b border-border">
            {DAY_NAMES.map((name) => (
              <div
                key={name}
                className="px-2 py-2 text-xs font-semibold text-muted-foreground text-center"
              >
                {name}
              </div>
            ))}
          </div>

          {/* Grid rows */}
          <div className="divide-y divide-border">
            {gridDays.map((week, weekIdx) => (
              <div key={weekIdx} className="grid grid-cols-7 divide-x divide-border">
                {week.map((date, dayIdx) => {
                  const isCurrentMonth = date.getMonth() === month && date.getFullYear() === year;
                  const daySugs = daySuggestions(date);
                  return (
                    <div
                      key={dayIdx}
                      className={cn(
                        "min-h-[100px] p-1.5 space-y-1 transition-colors",
                        isCurrentMonth ? "bg-background" : "bg-muted/20",
                      )}
                    >
                      <span
                        className={cn(
                          "inline-flex items-center justify-center h-6 w-6 text-xs font-medium rounded-full",
                          !isCurrentMonth && "text-muted-foreground/40",
                          isToday(date) &&
                            "bg-primary text-primary-foreground",
                        )}
                      >
                        {date.getDate()}
                      </span>
                      <div className="space-y-1">
                        {daySugs.slice(0, 3).map((sug) => (
                          <button
                            key={sug.id}
                            type="button"
                            onClick={() => setSelectedSuggestion(sug)}
                            className={cn(
                              "w-full text-left p-1 rounded text-[11px] leading-tight border transition-colors cursor-pointer",
                              sug.status === "pending" &&
                                "border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20",
                              sug.status === "approved" &&
                                "border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/20",
                              sug.status === "rejected" &&
                                "border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-950/20 opacity-60",
                              sug.status === "published" &&
                                "border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20",
                            )}
                          >
                            <div className="flex items-center gap-1 mb-0.5">
                              <PlatformIcon
                                platform={sug.platform}
                                className="[&_svg]:h-3 [&_svg]:w-3 shrink-0"
                              />
                              <span className="truncate font-medium text-muted-foreground">
                                {sug.content.length > 50
                                  ? `${sug.content.slice(0, 50)}…`
                                  : sug.content}
                              </span>
                            </div>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-[10px] px-1 py-0 h-auto font-normal",
                                sug.status === "pending" && "border-amber-300 text-amber-700 dark:text-amber-400",
                                sug.status === "approved" && "border-blue-300 text-blue-700 dark:text-blue-400",
                                sug.status === "rejected" && "border-red-300 text-red-700 dark:text-red-400",
                                sug.status === "published" && "border-emerald-300 text-emerald-700 dark:text-emerald-400",
                              )}
                            >
                              {sug.status}
                            </Badge>
                          </button>
                        ))}
                        {daySugs.length > 3 && (
                          <span className="text-[10px] text-muted-foreground block text-center">
                            +{daySugs.length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Generate dialog */}
      <Dialog open={showGenerate} onOpenChange={setShowGenerate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Suggestions</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="dayCount">Number of days</Label>
              <Input
                id="dayCount"
                type="number"
                min={1}
                max={30}
                value={genDayCount}
                onChange={(e) => setGenDayCount(Math.max(1, Math.min(30, Number(e.target.value))))}
              />
            </div>
            <div className="space-y-2">
              <Label>Platforms</Label>
              <div className="flex flex-col gap-2">
                  {(["x", "instagram", "linkedin"] as SuggestionPlatform[]).map((platform) => (
                  <label
                    key={platform}
                    className="flex items-center gap-2 text-sm cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={genPlatforms.includes(platform)}
                      onChange={() => toggleGenPlatform(platform)}
                      className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                    />
                    <PlatformIcon
                      platform={platform}
                      className="[&_svg]:h-4 [&_svg]:w-4"
                    />
                    <span className="capitalize">{platform}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGenerate(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => void handleGenerate()}
              disabled={generating || genPlatforms.length === 0}
            >
              {generating && <Loader2 className="h-4 w-4 animate-spin" />}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Detail sheet */}
      <SheetPanel
        title={
          <div className="flex items-center gap-2">
            {selectedSuggestion && (
              <PlatformIcon
                platform={selectedSuggestion.platform}
                className="[&_svg]:h-4 [&_svg]:w-4"
              />
            )}
            <span>Suggestion Detail</span>
          </div>
        }
        open={!!selectedSuggestion}
        onOpenChange={(open) => !open && setSelectedSuggestion(null)}
        width="md"
        footer={
          selectedSuggestion &&
          selectedSuggestion.status !== "published" && (
            <div className="flex items-center gap-2 w-full">
              {selectedSuggestion.status === "pending" && (
                <>
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => void handleReject(selectedSuggestion)}
                    disabled={operatingId === selectedSuggestion.id}
                  >
                    {operatingId === selectedSuggestion.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Reject
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={() => void handleApprove(selectedSuggestion)}
                    disabled={operatingId === selectedSuggestion.id}
                  >
                    {operatingId === selectedSuggestion.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : null}
                    Approve
                  </Button>
                </>
              )}
              {selectedSuggestion.status === "approved" && (
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => void handleReject(selectedSuggestion)}
                  disabled={operatingId === selectedSuggestion.id}
                >
                  {operatingId === selectedSuggestion.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : null}
                  Reject
                </Button>
              )}
              {selectedSuggestion.status === "rejected" && (
                <Button
                  className="flex-1"
                  onClick={() => void handleApprove(selectedSuggestion)}
                  disabled={operatingId === selectedSuggestion.id}
                >
                  {operatingId === selectedSuggestion.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : null}
                  Approve
                </Button>
              )}
            </div>
          )
        }
      >
        {selectedSuggestion && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="outline">
                <span className="capitalize">{selectedSuggestion.platform}</span>
              </Badge>
              <StatusBadge variant={STATUS_VARIANT[selectedSuggestion.status]}>
                {selectedSuggestion.status}
              </StatusBadge>
            </div>

            <div className="text-xs text-muted-foreground space-y-1">
              <p>
                Suggested for:{" "}
                {new Date(selectedSuggestion.suggested_for_date).toLocaleDateString(
                  "en-US",
                  { weekday: "long", month: "long", day: "numeric", year: "numeric" },
                )}
              </p>
              {selectedSuggestion.scheduled_at && (
                <p>
                  Scheduled:{" "}
                  {new Date(selectedSuggestion.scheduled_at).toLocaleString()}
                </p>
              )}
              {selectedSuggestion.published_at && (
                <p>
                  Published:{" "}
                  {new Date(selectedSuggestion.published_at).toLocaleString()}
                </p>
              )}
            </div>

            <div className="rounded-lg border border-border bg-muted/20 p-4">
              <p className="text-sm whitespace-pre-wrap leading-relaxed">
                {selectedSuggestion.content}
              </p>
            </div>
          </div>
        )}
      </SheetPanel>
    </div>
  );
}
