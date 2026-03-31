"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { EmptyState, KpiCard, Tabs, Skeleton } from "@/components/ui";
import { getCitations, getSourceDomains, getSourceGaps, CitationItem, apiRequest, type BrandProfile } from "@/lib/api";
import { useSelectedProjectId } from "@/lib/use-selected-project";

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
  const toast = useToast();
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
        toast.error("Failed to load source data", msg);
      }
    }
    setLoading(false);
  }

  const ownedDomainItems = domains.filter((domainItem) => isOwnedDomain(domainItem.domain, ownedWebsiteHost));
  const ownedSources = ownedDomainItems.length;

  if (loading) {
    return (
      <div>
        <h2 className="page-title" style={{ marginBottom: 24 }}>Source Intelligence</h2>
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

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 className="page-title">Source Intelligence</h2>
        <p className="text-muted">Understand which domains and URLs AI models cite when responding to prompts about your category.</p>
      </div>

      {/* KPI Row - 4 cards */}
      <div className="data-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 32, gap: 16 }}>
        <KpiCard label="Unique Domains" value={uniqueDomains} />
        <KpiCard label="Total Citations" value={citationTotal} />
        <KpiCard label="Sources We Own" value={ownedSources} />
        <KpiCard label="Source Gaps" value={gaps.length} />
      </div>

      <Tabs
        tabs={[
          { key: "all", label: "All Citations", count: citationTotal },
          { key: "owned", label: "Our Sources", count: ownedSources },
          { key: "gaps", label: "Source Gaps", count: gaps.length },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      <div style={{ marginTop: 20 }}>
        {/* Tab 1: All Citations */}
        {activeTab === "all" && (
          citations.length === 0 ? (
            <EmptyState
              icon="📝"
              title="No citations found yet"
              description="Citations are automatically extracted from AI model responses when you run prompt sets on the AI Visibility page."
            />
          ) : (
            <div className="table-list">
              <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", height: 40 }}>
                    <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Domain</th>
                    <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>URL</th>
                    <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Platform</th>
                    <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Type</th>
                    <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>First Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {citations.slice(0, 50).map(c => (
                    <tr key={c.id} style={{ borderBottom: "1px solid var(--border)", height: 40 }}>
                      <td style={{ padding: "8px 12px", fontWeight: 600 }}>{c.domain}</td>
                      <td style={{ padding: "8px 12px", maxWidth: 350, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", textDecoration: "none" }}>
                          {c.url}
                        </a>
                      </td>
                      <td style={{ padding: "8px 12px" }}>
                        <span className="badge" style={{ fontSize: 11 }}>AI Response</span>
                      </td>
                      <td style={{ padding: "8px 12px" }}>
                        <span className="badge" style={{ fontSize: 11 }}>{c.content_type || "Page"}</span>
                      </td>
                      <td style={{ padding: "8px 12px", color: "var(--text-muted)", fontSize: 12 }}>
                        {c.first_seen_at ? new Date(c.first_seen_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {/* Tab 2: Our Sources */}
        {activeTab === "owned" && (
          <div>
            {ownedSources === 0 ? (
              <EmptyState
                icon="🏢"
                title="No owned sources yet"
                description="Sources you own are identified from your brand profile. Set up your brand to track which of the cited domains are yours."
              />
            ) : (
              <div className="table-list">
                <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border)", height: 40 }}>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Domain</th>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Citations</th>
                      <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)" }}>Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ownedDomainItems.map(d => {
                        const share = citationTotal > 0 ? Math.round((d.total_citations / citationTotal) * 100) : 0;
                        return (
                          <tr key={d.domain} style={{ borderBottom: "1px solid var(--border)", height: 40 }}>
                            <td style={{ padding: "8px 12px", fontWeight: 600 }}>{d.domain}</td>
                            <td style={{ padding: "8px 12px" }}>{d.total_citations}</td>
                            <td style={{ padding: "8px 12px" }}>
                              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <div style={{
                                  width: 60,
                                  height: 6,
                                  backgroundColor: "var(--surface)",
                                  borderRadius: 3,
                                  overflow: "hidden"
                                }}>
                                  <div style={{
                                    width: `${share}%`,
                                    height: "100%",
                                    backgroundColor: "var(--accent)"
                                  }} />
                                </div>
                                <span style={{ fontSize: 12 }}>{share}%</span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Source Gaps */}
        {activeTab === "gaps" && (
          gaps.length === 0 ? (
            <EmptyState
              icon="🔍"
              title="No source gaps detected"
              description="Source gaps show where competitors are cited by AI but your brand is not. Run visibility tracking to discover gaps."
            />
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {gaps.map(g => (
                <div
                  key={g.id}
                  className="card"
                  style={{
                    padding: 14,
                    display: "grid",
                    gridTemplateColumns: "1fr auto",
                    gap: 12,
                    alignItems: "center"
                  }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>
                      <span style={{ color: "var(--accent)" }}>{g.competitor_name}</span> is cited on{" "}
                      <span style={{ fontWeight: 700 }}>{g.domain}</span>
                    </div>
                    <p className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                      Your brand is not cited on this domain. Consider creating content there to close the gap.
                    </p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "var(--accent)" }}>{g.citation_count}</div>
                    <div className="text-muted" style={{ fontSize: 11 }}>citation{g.citation_count !== 1 ? "s" : ""}</div>
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
