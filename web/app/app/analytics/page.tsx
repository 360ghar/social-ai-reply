"use client";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { apiRequest } from "@/lib/api";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { withProjectId } from "@/lib/project";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface AnalyticsOverview {
  visibility_score: number;
  total_opportunities: number;
  total_drafts: number;
  total_published: number;
}

interface TrendData {
  date: string | null;
  visibility_score: number;
}

interface EngagementData {
  by_status: Record<string, number>;
  total_scans: number;
}

interface KeywordData {
  keyword: string;
  priority_score: number;
}

interface SubredditData {
  name: string;
  fit_score: number;
}

interface ActivityEvent {
  id: number;
  action: string;
  entity_type: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

function toTitleCase(value: string) {
  return value.replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatActivityLabel(event: ActivityEvent) {
  const metadataTitle = typeof event.metadata?.title === "string" ? event.metadata.title : null;
  if (metadataTitle) {
    return metadataTitle;
  }

  const action = toTitleCase(event.action.replace(/[._]/g, " "));
  const entityType = event.entity_type ? toTitleCase(event.entity_type.replace(/_/g, " ")) : "";
  return entityType ? `${action} · ${entityType}` : action;
}

export default function AnalyticsPage() {
  const { token } = useAuth();
  const { success, error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<"7d" | "30d" | "90d" | "all">("30d");
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [engagementData, setEngagementData] = useState<EngagementData | null>(null);
  const [keywords, setKeywords] = useState<KeywordData[]>([]);
  const [subreddits, setSubreddits] = useState<SubredditData[]>([]);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, selectedProjectId, dateRange]);

  async function loadData() {
    setLoading(true);
    try {
      const days = dateRange === "7d" ? 7 : dateRange === "30d" ? 30 : dateRange === "90d" ? 90 : 365;

      const [overviewRes, trendRes, funnelRes, keywordsRes, subredditsRes, activityRes] = await Promise.allSettled([
        apiRequest<AnalyticsOverview>(
          withProjectId(`/v1/analytics/overview?days=${days}`, selectedProjectId),
          {},
          token
        ),
        apiRequest<{ items: TrendData[] }>(
          withProjectId(`/v1/analytics/visibility-trend?days=${days}`, selectedProjectId),
          {},
          token
        ),
        apiRequest<EngagementData>(
          withProjectId(`/v1/analytics/engagement`, selectedProjectId),
          {},
          token
        ),
        apiRequest<{ items: KeywordData[] }>(
          withProjectId(`/v1/analytics/keywords`, selectedProjectId),
          {},
          token
        ),
        apiRequest<{ items: SubredditData[] }>(
          withProjectId(`/v1/analytics/subreddits`, selectedProjectId),
          {},
          token
        ),
        apiRequest<{ items: ActivityEvent[] }>(
          withProjectId(`/v1/activity`, selectedProjectId),
          {},
          token
        ),
      ]);

      if (overviewRes.status === "fulfilled") setOverview(overviewRes.value);
      if (trendRes.status === "fulfilled") setTrendData(trendRes.value.items || []);
      if (funnelRes.status === "fulfilled") setEngagementData(funnelRes.value);
      if (keywordsRes.status === "fulfilled") setKeywords(keywordsRes.value.items || []);
      if (subredditsRes.status === "fulfilled") setSubreddits(subredditsRes.value.items || []);
      if (activityRes.status === "fulfilled") setActivity(activityRes.value.items || []);
    } catch (e: any) {
      error("Failed to load analytics", e?.message);
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div>
        <h2 className="text-2xl font-semibold mb-6">Analytics</h2>
        <div className="grid grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => (
            <Card key={i} className="p-4">
              <Skeleton className="h-8 w-3/5 mb-2" />
              <Skeleton className="h-3 w-full" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const firstTrendPoint = trendData[0]?.visibility_score ?? overview?.visibility_score ?? 0;
  const lastTrendPoint = trendData[trendData.length - 1]?.visibility_score ?? overview?.visibility_score ?? 0;
  const visibilityTrend = Math.round((lastTrendPoint - firstTrendPoint) * 10) / 10;
  const trendDir = visibilityTrend >= 0 ? "↑" : "↓";
  const trendColor = visibilityTrend >= 0 ? "text-emerald-600" : "text-destructive";

  // Max values for bar heights
  const maxTrendScore = Math.max(...trendData.map(d => d.visibility_score), 100);
  const maxKeywords = Math.max(...keywords.map(k => k.priority_score), 1);
  const maxSubreddits = Math.max(...subreddits.map(s => s.fit_score), 100);

  // Funnel calculations
  const byStatus = engagementData?.by_status || {};
  const funnelOpp = Object.values(byStatus).reduce((total, count) => total + count, 0);
  const funnelSaved = byStatus.saved || 0;
  const funnelDraft = byStatus.drafting || 0;
  const funnelPost = byStatus.posted || 0;
  const conv1 = funnelOpp > 0 ? Math.round((funnelSaved / funnelOpp) * 100) : 0;
  const conv2 = funnelSaved > 0 ? Math.round((funnelDraft / funnelSaved) * 100) : 0;
  const conv3 = funnelDraft > 0 ? Math.round((funnelPost / funnelDraft) * 100) : 0;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-semibold">Analytics Dashboard</h2>
          <p className="text-muted-foreground">Track visibility trends, engagement funnel, and performance metrics.</p>
        </div>
        <select
          value={dateRange}
          onChange={e => setDateRange(e.target.value as any)}
          className="rounded-lg border px-3 py-2 text-[13px]"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Card className="p-4">
          <div className="text-[28px] font-bold text-primary mb-1">
            {overview?.visibility_score || 0}%
            <span className={`text-base ml-2 ${trendColor}`}>
              {trendDir} {Math.abs(visibilityTrend)} pts
            </span>
          </div>
          <div className="text-[13px] text-muted-foreground">Visibility Score</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{overview?.total_opportunities || 0}</div>
          <div className="text-xs text-muted-foreground">Opportunities Found</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{overview?.total_drafts || 0}</div>
          <div className="text-xs text-muted-foreground">Drafts Created</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{overview?.total_published || 0}</div>
          <div className="text-xs text-muted-foreground">Posts Published</div>
        </Card>
      </div>

      {/* Section 1: Visibility Trend Chart (CSS bars) */}
      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-4">Visibility Score Trend</h3>
        {trendData.length === 0 ? (
          <div className="text-center py-10 text-muted-foreground">
            <p className="text-[13px]">No trend data available yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-[auto_1fr] gap-4 items-end h-[200px]">
            {/* Y-axis labels */}
            <div className="flex flex-col-reverse justify-between text-[11px] text-muted-foreground">
              <span>0</span>
              <span>25</span>
              <span>50</span>
              <span>75</span>
              <span>100</span>
            </div>
            {/* Chart bars */}
            <div className="flex gap-3 items-end h-full border-b pb-2">
              {trendData.slice(-30).map((d, i) => (
                <div
                  key={i}
                  title={`${d.date || "Unknown date"}: ${d.visibility_score}`}
                  className="flex-1 min-w-0 min-h-[2px] bg-primary/80 rounded-t-sm"
                  style={{ height: `${(d.visibility_score / maxTrendScore) * 100}%` }}
                />
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Section 2: Engagement Funnel */}
      <Card className="p-5 mb-6">
        <h3 className="text-sm font-semibold mb-4">Engagement Funnel</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Based on opportunity status counts and {engagementData?.total_scans || 0} total scans.
        </p>
        <div className="space-y-4">
          {[
            { label: "Opportunities", value: funnelOpp, width: 100 },
            { label: "Saved", value: funnelSaved, width: (funnelSaved / funnelOpp) * 100 || 0, conv: conv1 },
            { label: "Drafted", value: funnelDraft, width: (funnelDraft / funnelOpp) * 100 || 0, conv: conv2 },
            { label: "Published", value: funnelPost, width: (funnelPost / funnelOpp) * 100 || 0, conv: conv3 },
          ].map((stage, i) => (
            <div key={i}>
              <div className="flex justify-between mb-1.5">
                <span className="text-[13px] font-semibold">{stage.label}</span>
                <div className="flex gap-2 text-xs">
                  <span><strong>{stage.value}</strong></span>
                  {stage.conv !== undefined && <span className="text-muted-foreground">{stage.conv}% conversion</span>}
                </div>
              </div>
              <div className="w-full h-8 bg-muted rounded-md overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-primary to-indigo-500 flex items-center justify-center text-white text-xs font-semibold transition-[width] duration-300"
                  style={{ width: `${Math.min(stage.width, 100)}%` }}
                >
                  {Math.round(stage.width)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Section 3: Two columns - Keywords & Subreddits */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Left: Top Keywords */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4">Top Keywords by Priority Score</h3>
          {keywords.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-[13px]">No keyword data yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {keywords.slice(0, 8).map((k, i) => (
                <div key={i} className="flex items-center gap-3 text-[13px]">
                  <span className="font-semibold min-w-[30px]">{i + 1}</span>
                  <span className="flex-1">{k.keyword}</span>
                  <div className="w-[60px] h-6 bg-muted rounded flex items-center justify-center overflow-hidden">
                    <div
                      className="h-full bg-primary flex items-center justify-center text-white text-[11px] font-semibold"
                      style={{ width: `${(k.priority_score / maxKeywords) * 100}%` }}
                    >
                      {k.priority_score > 0 ? Math.round(k.priority_score) : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Right: Top Subreddits */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold mb-4">Top Subreddits by Fit Score</h3>
          {subreddits.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-[13px]">No subreddit data yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {subreddits.slice(0, 8).map((s, i) => (
                <div key={i} className="flex items-center gap-3 text-[13px]">
                  <span className="font-semibold min-w-[30px]">{i + 1}</span>
                  <span className="flex-1">r/{s.name}</span>
                  <div className="w-[60px] h-6 bg-muted rounded flex items-center justify-center overflow-hidden">
                    <div
                      className="h-full bg-primary flex items-center justify-center text-white text-[11px] font-semibold"
                      style={{ width: `${(s.fit_score / maxSubreddits) * 100}%` }}
                    >
                      {Math.round(s.fit_score)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Section 4: Recent Activity Timeline */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold mb-4">Recent Activity</h3>
        {activity.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <span className="text-2xl mb-2">📊</span>
            <p className="font-medium">No activity yet</p>
            <p className="text-sm text-muted-foreground mt-1">Analytics data will appear as you use the platform. Run your first scan to get started.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activity.slice(0, 12).map(evt => (
              <div
                key={evt.id}
                className="flex items-center gap-3 p-3 bg-muted rounded-lg text-[13px]"
              >
                <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                <div className="flex-1">
                  <strong>{formatActivityLabel(evt)}</strong>
                </div>
                <div className="text-xs text-muted-foreground whitespace-nowrap">
                  {evt.created_at ? new Date(evt.created_at).toLocaleString() : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
