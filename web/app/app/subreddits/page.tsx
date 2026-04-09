"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { apiRequest, type Dashboard, type MonitoredSubreddit } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { ScoreBadge } from "@/components/shared/score-badge";

type SortOption = "fit-score" | "activity-score" | "name";

export default function SubredditsPage() {
  const { token } = useAuth();
  const { success, error: toastError } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [subreddits, setSubreddits] = useState<MonitoredSubreddit[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("fit-score");
  const [activeTab, setActiveTab] = useState<"all" | "top">("all");

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        toastError(err.message);
        setLoading(false);
      });
  }, [token, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setLoading(true);
    apiRequest<MonitoredSubreddit[]>(`/v1/discovery/subreddits?project_id=${project.id}`, {}, token)
      .then(setSubreddits)
      .catch((err) => toastError(err.message))
      .finally(() => setLoading(false));
  }, [project, token]);

  async function refreshAnalysis(subredditId: number) {
    if (!token) {
      return;
    }
    setRefreshingId(subredditId);
    try {
      const updated = await apiRequest<MonitoredSubreddit>(
        `/v1/subreddits/${subredditId}/analyze`,
        { method: "POST" },
        token
      );
      setSubreddits((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      success("Analysis refreshed");
    } catch (err) {
      toastError((err as Error).message);
    } finally {
      setRefreshingId(null);
    }
  }

  // Filter communities based on tab and search query
  const filteredSubreddits = subreddits
    .filter((s) => {
      if (activeTab === "top" && s.fit_score < 70) {
        return false;
      }
      return s.name.toLowerCase().includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "fit-score":
          return b.fit_score - a.fit_score;
        case "activity-score":
          return b.activity_score - a.activity_score;
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

  // Calculate KPI metrics
  const avgFitScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.fit_score, 0) / subreddits.length) : 0;
  const avgActivityScore = subreddits.length ? Math.round(subreddits.reduce((sum, s) => sum + s.activity_score, 0) / subreddits.length) : 0;
  const activeCount = subreddits.filter((s) => s.is_active).length;

  return (
    <div className="flex flex-col gap-8">
      {/* Header Section */}
      <Card className="p-6">
        <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Community Coverage</div>
        <h2 className="text-xl font-bold mb-2">Review which communities deserve active engagement</h2>
        <p className="text-sm text-muted-foreground">
          Today this page is Reddit-specific, but the scoring model is the right shape for a broader product: fit, activity, moderation risk, and audience signals should work across forums, Q and A spaces, and social comment surfaces.
        </p>
        <div className="flex flex-wrap gap-2 mt-4">
          <Badge>Reddit live now</Badge>
          <Badge variant="secondary">Q and A pattern ready</Badge>
          <Badge variant="secondary">Forum pattern ready</Badge>
        </div>
        {message && (
          <div className="mt-4 rounded-md bg-muted px-4 py-3 text-sm">{message}</div>
        )}
      </Card>

      {/* KPI Cards */}
      {!loading && subreddits.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="text-2xl font-bold">{subreddits.length}</div>
            <div className="text-xs text-muted-foreground">Total Communities</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold">{avgFitScore}</div>
            <div className="text-xs text-muted-foreground">Avg Fit Score</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold">{avgActivityScore}</div>
            <div className="text-xs text-muted-foreground">Avg Activity Score</div>
          </Card>
          <Card className="p-4">
            <div className="text-2xl font-bold">{activeCount}</div>
            <div className="text-xs text-muted-foreground">Active</div>
          </Card>
        </div>
      )}

      {/* Communities List */}
      <Card className="p-6">
        {/* Controls */}
        {!loading && subreddits.length > 0 && (
          <div className="mb-6">
            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "all" | "top")} className="mb-6">
              <TabsList>
                <TabsTrigger value="all">All Communities</TabsTrigger>
                <TabsTrigger value="top">Top Performers</TabsTrigger>
              </TabsList>
            </Tabs>

            {/* Search and Sort */}
            <div className="flex gap-4 mb-6">
              <div className="flex-1 space-y-2">
                <Input
                  type="text"
                  placeholder="Filter by subreddit name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="h-8 rounded-lg border border-input bg-transparent px-2.5 py-1 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                >
                  <option value="fit-score">Sort by Fit Score</option>
                  <option value="activity-score">Sort by Activity Score</option>
                  <option value="name">Sort by Name</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center p-8">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )}

        {/* Communities */}
        {!loading && filteredSubreddits.length > 0 && (
          <div className="space-y-4">
            {filteredSubreddits.map((subreddit) => (
              <div key={subreddit.id} className="rounded-lg border bg-card p-4">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <strong className="text-lg">r/{subreddit.name}</strong>
                    {subreddit.title && (
                      <p className="mt-1 text-sm text-muted-foreground">{subreddit.title}</p>
                    )}
                  </div>
                  <Button
                    onClick={() => refreshAnalysis(subreddit.id)}
                    disabled={refreshingId === subreddit.id}
                    variant="outline"
                    size="sm"
                  >
                    {refreshingId === subreddit.id ? (
                      <span className="inline-flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Refreshing...
                      </span>
                    ) : (
                      "Refresh Analysis"
                    )}
                  </Button>
                </div>

                {/* Description */}
                {subreddit.description && (
                  <p className="mb-4 text-sm text-muted-foreground">
                    {subreddit.description}
                  </p>
                )}

                {/* Scores */}
                <div className="flex flex-wrap gap-2 mb-4">
                  <Badge variant="secondary">Fit</Badge>
                  <ScoreBadge score={subreddit.fit_score} />
                  <Badge variant="secondary">Activity</Badge>
                  <ScoreBadge score={subreddit.activity_score} />
                </div>

                {/* Subscriber Count */}
                <div className="mb-4 text-sm text-muted-foreground">
                  {subreddit.subscribers.toLocaleString()} subscribers
                </div>

                {/* Analysis */}
                {subreddit.analyses[0] && (
                  <div className="mb-4 rounded-md bg-muted px-4 py-3 text-sm">
                    <strong>Recommendation:</strong> {subreddit.analyses[0].recommendation}
                    {subreddit.analyses[0].audience_signals.length > 0 && (
                      <>
                        <br />
                        <strong className="text-sm">Audience signals:</strong> {subreddit.analyses[0].audience_signals.join(", ")}
                      </>
                    )}
                  </div>
                )}

                {/* Rules Summary */}
                {subreddit.rules_summary && (
                  <div className="text-sm text-muted-foreground">
                    <strong>Rules to watch:</strong> {subreddit.rules_summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Empty States */}
        {!loading && filteredSubreddits.length === 0 && subreddits.length === 0 && (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <h3 className="text-lg font-semibold mb-1">No communities yet</h3>
            <p className="text-sm text-muted-foreground">
              Use the Find posts page to discover communities first.
            </p>
          </div>
        )}

        {!loading && filteredSubreddits.length === 0 && subreddits.length > 0 && (
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <h3 className="text-lg font-semibold mb-1">No communities match your filter</h3>
            <p className="text-sm text-muted-foreground">
              Try adjusting your search or sort options.
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
