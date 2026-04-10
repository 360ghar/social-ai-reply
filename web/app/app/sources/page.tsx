"use client";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { getCitations, getSourceDomains, getSourceGaps, CitationItem, apiRequest, type BrandProfile } from "@/lib/api";
import { useSelectedProjectId } from "@/hooks/use-selected-project";

interface SourceDomain {
  domain: string;
  total_citations: number;
}

interface SourceGap {
  id: number;
  competitor_name: string;
  domain: string;
  citation_count: number;
}

function normalizeHostname(value: string | null | undefined) {
  if (!value) {
    return null;
  }

  try {
    const parsed = new URL(value.includes("://") ? value : `https://${value}`);
    return parsed.hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return value.toLowerCase().replace(/^www\./, "").replace(/\/.*$/, "");
  }
}

function isOwnedDomain(domain: string, ownedWebsiteHost: string | null) {
  const normalizedDomain = normalizeHostname(domain);
  if (!normalizedDomain || !ownedWebsiteHost) {
    return false;
  }

  return (
    normalizedDomain === ownedWebsiteHost
    || normalizedDomain.endsWith(`.${ownedWebsiteHost}`)
    || ownedWebsiteHost.endsWith(`.${normalizedDomain}`)
  );
}

export default function SourcesPage() {
  const { token } = useAuth();
  const { error } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");
  const [domains, setDomains] = useState<SourceDomain[]>([]);
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [gaps, setGaps] = useState<SourceGap[]>([]);
  const [uniqueDomains, setUniqueDomains] = useState(0);
  const [citationTotal, setCitationTotal] = useState(0);
  const [ownedWebsiteHost, setOwnedWebsiteHost] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, selectedProjectId]);

  async function loadData() {
    setLoading(true);
    try {
      const [domRes, citRes, gapRes, brandRes] = await Promise.allSettled([
        getSourceDomains(token!, selectedProjectId),
        getCitations(token!, undefined, 100, selectedProjectId),
        getSourceGaps(token!, selectedProjectId),
        selectedProjectId ? apiRequest<BrandProfile>(`/v1/brand/${selectedProjectId}`, {}, token) : Promise.resolve(null),
      ]);

      if (domRes.status === "fulfilled") {
        setDomains(domRes.value.items || []);
        setUniqueDomains(domRes.value.items?.length || 0);
      }
      if (citRes.status === "fulfilled") {
        setCitations(citRes.value.items || []);
        setCitationTotal(citRes.value.total || 0);
      }
      if (gapRes.status === "fulfilled") {
        setGaps(gapRes.value.items || []);
      }
      if (brandRes.status === "fulfilled") {
        setOwnedWebsiteHost(normalizeHostname(brandRes.value?.website_url));
      } else {
        setOwnedWebsiteHost(null);
      }
    } catch (e: any) {
      const msg = e?.message || "";
      if (!msg.includes("No active project") && !msg.includes("Not Found") && !msg.includes("404")) {
        error("Failed to load source data", msg);
      }
    }
    setLoading(false);
  }

  const ownedDomainItems = domains.filter((domainItem) => isOwnedDomain(domainItem.domain, ownedWebsiteHost));
  const ownedSources = ownedDomainItems.length;

  if (loading) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-6">Source Intelligence</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
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

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Source Intelligence</h2>
        <p className="text-muted-foreground">Understand which domains and URLs AI models cite when responding to prompts about your category.</p>
      </div>

      {/* KPI Row - 4 cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Card className="p-4">
          <div className="text-2xl font-bold">{uniqueDomains}</div>
          <div className="text-xs text-muted-foreground">Unique Domains</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{citationTotal}</div>
          <div className="text-xs text-muted-foreground">Total Citations</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{ownedSources}</div>
          <div className="text-xs text-muted-foreground">Sources We Own</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold">{gaps.length}</div>
          <div className="text-xs text-muted-foreground">Source Gaps</div>
        </Card>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">
            All Citations
            <Badge variant="secondary" className="ml-1.5">{citationTotal}</Badge>
          </TabsTrigger>
          <TabsTrigger value="owned">
            Our Sources
            <Badge variant="secondary" className="ml-1.5">{ownedSources}</Badge>
          </TabsTrigger>
          <TabsTrigger value="gaps">
            Source Gaps
            <Badge variant="secondary" className="ml-1.5">{gaps.length}</Badge>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: All Citations */}
        <TabsContent value="all" className="mt-5">
          {citations.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="text-4xl mb-3">📝</div>
              <h3 className="text-lg font-semibold mb-1">No citations found yet</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Citations are automatically extracted from AI model responses when you run prompt sets on the AI Visibility page.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Domain</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">URL</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Platform</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Type</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">First Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {citations.slice(0, 50).map(c => (
                    <tr key={c.id} className="border-b last:border-b-0 h-10">
                      <td className="p-3 font-semibold">{c.domain}</td>
                      <td className="p-3 max-w-[350px] overflow-hidden text-ellipsis whitespace-nowrap">
                        <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                          {c.url}
                        </a>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary">AI Response</Badge>
                      </td>
                      <td className="p-3">
                        <Badge variant="secondary">{c.content_type || "Page"}</Badge>
                      </td>
                      <td className="p-3 text-xs text-muted-foreground">
                        {c.first_seen_at ? new Date(c.first_seen_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Our Sources */}
        <TabsContent value="owned" className="mt-5">
          {ownedSources === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="text-4xl mb-3">🏢</div>
              <h3 className="text-lg font-semibold mb-1">No owned sources yet</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Sources you own are identified from your brand profile. Set up your brand to track which of the cited domains are yours.
              </p>
            </div>
          ) : (
            <div className="rounded-lg border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Domain</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Citations</th>
                    <th className="p-3 text-left text-xs font-semibold uppercase text-muted-foreground">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {ownedDomainItems.map(d => {
                    const share = citationTotal > 0 ? Math.round((d.total_citations / citationTotal) * 100) : 0;
                    return (
                      <tr key={d.domain} className="border-b last:border-b-0 h-10">
                        <td className="p-3 font-semibold">{d.domain}</td>
                        <td className="p-3">{d.total_citations}</td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full"
                                style={{ width: `${share}%` }}
                              />
                            </div>
                            <span className="text-xs">{share}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        {/* Tab 3: Source Gaps */}
        <TabsContent value="gaps" className="mt-5">
          {gaps.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="text-4xl mb-3">🔍</div>
              <h3 className="text-lg font-semibold mb-1">No source gaps detected</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Source gaps show where competitors are cited by AI but your brand is not. Run visibility tracking to discover gaps.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {gaps.map(g => (
                <div
                  key={g.id}
                  className="rounded-lg border bg-card p-4 grid grid-cols-[1fr_auto] gap-3 items-center"
                >
                  <div>
                    <div className="text-sm font-semibold">
                      <span className="text-primary">{g.competitor_name}</span> is cited on{" "}
                      <span className="font-bold">{g.domain}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Your brand is not cited on this domain. Consider creating content there to close the gap.
                    </p>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-primary">{g.citation_count}</div>
                    <div className="text-xs text-muted-foreground">citation{g.citation_count !== 1 ? "s" : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
