"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, EmptyState, KpiCard, Spinner, Skeleton } from "@/components/ui";
import { apiRequest } from "@/lib/api";
import { useSelectedProjectId } from "@/lib/use-selected-project";
import { withProjectId } from "@/lib/project";

interface AnalyticsOverview {
  visibility_score: number;
  visibility_trend?: number;
  opportunities_found: number;
  drafts_created: number;
  posts_published: number;
}

interface TrendData {
  date: string;
  score: number;
}

interface FunnelData {
  opportunities: number;
  saved: number;
  drafted: number;
  posted: number;
}

interface KeywordData {
  keyword: string;
  opportunities_count: number;
}

interface SubredditData {
  name: string;
  fit_score: number;
}

interface ActivityEvent {
  id: number;
  type: string;
  title: string;
  created_at: string;
}

export default function AnalyticsPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<"7d" | "30d" | "90d" | "all">("30d");
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
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
        apiRequest<FunnelData>(
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
      if (funnelRes.status === "fulfilled") setFunnelData(funnelRes.value);
      if (keywordsRes.status === "fulfilled") setKeywords(keywordsRes.value.items || []);
      if (subredditsRes.status === "fulfilled") setSubreddits(subredditsRes.value.items || []);
      if (activityRes.status === "fulfilled") setActivity(activityRes.value.items || []);
    } catch (e: any) {
      console.error("Analytics load failed:", e);
      toast.error("Failed to load analytics", e?.message);
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div>
        <h2 className="page-title" style={{ marginBottom: 24 }}>Analytics</h2>
        <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 32, gap: 16 }}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card" style={{ padding: 16 }}>
              <Skeleton height={32} width="60%" style={{ marginBottom: 8 }} />
              <Skeleton height={12} width="100%" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Calculate trend arrow
  const trendDir = (overview?.visibility_trend ?? 0) >= 0 ? "↑" : "↓";
  const trendColor = (overview?.visibility_trend ?? 0) >= 0 ? "var(--success)" : "var(--error)";

  // Max values for bar heights
  const maxTrendScore = Math.max(...trendData.map(d => d.score), 100);
  const maxKeywords = Math.max(...keywords.map(k => k.opportunities_count), 1);
  const maxSubreddits = Math.max(...subreddits.map(s => s.fit_score), 100);

  // Funnel calculations
  const funnelOpp = funnelData?.opportunities || 0;
  const funnelSaved = funnelData?.saved || 0;
  const funnelDraft = funnelData?.drafted || 0;
  const funnelPost = funnelData?.posted || 0;
  const conv1 = funnelOpp > 0 ? Math.round((funnelSaved / funnelOpp) * 100) : 0;
  const conv2 = funnelSaved > 0 ? Math.round((funnelDraft / funnelSaved) * 100) : 0;
  const conv3 = funnelDraft > 0 ? Math.round((funnelPost / funnelDraft) * 100) : 0;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h2 className="page-title">Analytics Dashboard</h2>
          <p className="text-muted">Track visibility trends, engagement funnel, and performance metrics.</p>
        </div>
        <select
          value={dateRange}
          onChange={e => setDateRange(e.target.value as any)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border)", fontSize: 13 }}
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      {/* KPI Row */}
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 32, gap: 16 }}>
        <div className="kpi-card card" style={{ padding: 16 }}>
          <div style={{ fontSize: 28, fontWeight: 700, color: "var(--accent)", marginBottom: 4 }}>
            {overview?.visibility_score || 0}%
            <span style={{ fontSize: 16, color: trendColor, marginLeft: 8 }}>
              {trendDir} {Math.abs(overview?.visibility_trend || 0)}%
            </span>
          </div>
          <div className="text-muted" style={{ fontSize: 13 }}>Visibility Score</div>
        </div>
        <KpiCard label="Opportunities Found" value={overview?.opportunities_found || 0} />
        <KpiCard label="Drafts Created" value={overview?.drafts_created || 0} />
        <KpiCard label="Posts Published" value={overview?.posts_published || 0} />
      </div>

      {/* Section 1: Visibility Trend Chart (CSS bars) */}
      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Visibility Score Trend</h3>
        {trendData.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>
            <p style={{ fontSize: 13 }}>No trend data available yet</p>
          </div>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            gap: 16,
            alignItems: "flex-end",
            height: 200
          }}>
            {/* Y-axis labels */}
            <div style={{ display: "flex", flexDirection: "column-reverse", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)" }}>
              <span>0</span>
              <span>25</span>
              <span>50</span>
              <span>75</span>
              <span>100</span>
            </div>
            {/* Chart bars */}
            <div style={{
              display: "flex",
              gap: 12,
              alignItems: "flex-end",
              height: "100%",
              borderBottom: "1px solid var(--border)",
              paddingBottom: 8
            }}>
              {trendData.slice(-30).map((d, i) => (
                <div
                  key={i}
                  title={`${d.date}: ${d.score}`}
                  style={{
                    flex: 1,
                    minWidth: 0,
                    height: `${(d.score / maxTrendScore) * 100}%`,
                    backgroundColor: "var(--accent)",
                    borderRadius: "2px 2px 0 0",
                    opacity: 0.8,
                    minHeight: 2
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Engagement Funnel */}
      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Engagement Funnel</h3>
        <div style={{ display: "grid", gap: 16 }}>
          {[
            { label: "Opportunities", value: funnelOpp, width: 100 },
            { label: "Saved", value: funnelSaved, width: (funnelSaved / funnelOpp) * 100 || 0, conv: conv1 },
            { label: "Drafted", value: funnelDraft, width: (funnelDraft / funnelOpp) * 100 || 0, conv: conv2 },
            { label: "Published", value: funnelPost, width: (funnelPost / funnelOpp) * 100 || 0, conv: conv3 },
          ].map((stage, i) => (
            <div key={i}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{stage.label}</span>
                <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
                  <span><strong>{stage.value}</strong></span>
                  {stage.conv !== undefined && <span className="text-muted">{stage.conv}% conversion</span>}
                </div>
              </div>
              <div style={{
                width: "100%",
                height: 32,
                backgroundColor: "var(--surface)",
                borderRadius: 6,
                overflow: "hidden"
              }}>
                <div style={{
                  width: `${Math.min(stage.width, 100)}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, var(--accent), var(--indigo))`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "white",
                  fontSize: 12,
                  fontWeight: 600,
                  transition: "width 0.3s ease"
                }}>
                  {Math.round(stage.width)}%
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Two columns - Keywords & Subreddits */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        {/* Left: Top Keywords */}
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top Keywords by Opportunities</h3>
          {keywords.length === 0 ? (
            <div style={{ textAlign: "center", padding: 30, color: "var(--text-muted)" }}>
              <p style={{ fontSize: 13 }}>No keyword data yet</p>
            </div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {keywords.slice(0, 8).map((k, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
                  <span style={{ fontWeight: 600, minWidth: 30 }}>{i + 1}</span>
                  <span style={{ flex: 1 }}>{k.keyword}</span>
                  <div style={{
                    width: 60,
                    height: 24,
                    backgroundColor: "var(--surface)",
                    borderRadius: 4,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden"
                  }}>
                    <div style={{
                      width: `${(k.opportunities_count / maxKeywords) * 100}%`,
                      height: "100%",
                      backgroundColor: "var(--accent)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "white",
                      fontSize: 11,
                      fontWeight: 600
                    }}>
                      {k.opportunities_count > 0 ? k.opportunities_count : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Top Subreddits */}
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top Subreddits by Fit Score</h3>
          {subreddits.length === 0 ? (
            <div style={{ textAlign: "center", padding: 30, color: "var(--text-muted)" }}>
              <p style={{ fontSize: 13 }}>No subreddit data yet</p>
            </div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {subreddits.slice(0, 8).map((s, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 13 }}>
                  <span style={{ fontWeight: 600, minWidth: 30 }}>{i + 1}</span>
                  <span style={{ flex: 1 }}>r/{s.name}</span>
                  <div style={{
                    width: 60,
                    height: 24,
                    backgroundColor: "var(--surface)",
                    borderRadius: 4,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden"
                  }}>
                    <div style={{
                      width: `${(s.fit_score / maxSubreddits) * 100}%`,
                      height: "100%",
                      backgroundColor: "var(--accent)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "white",
                      fontSize: 11,
                      fontWeight: 600
                    }}>
                      {Math.round(s.fit_score)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Section 4: Recent Activity Timeline */}
      <div className="card" style={{ padding: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Recent Activity</h3>
        {activity.length === 0 ? (
          <EmptyState
            icon="📊"
            title="No activity yet"
            description="Analytics data will appear as you use the platform. Run your first scan to get started."
          />
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            {activity.slice(0, 12).map(evt => (
              <div
                key={evt.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: 12,
                  backgroundColor: "var(--surface)",
                  borderRadius: 8,
                  fontSize: 13
                }}
              >
                <div style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: "var(--accent)",
                  flexShrink: 0
                }} />
                <div style={{ flex: 1 }}>
                  <strong>{evt.title || evt.type.replace(/_/g, " ")}</strong>
                </div>
                <div className="text-muted" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                  {evt.created_at ? new Date(evt.created_at).toLocaleString() : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
