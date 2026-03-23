"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { EmptyState, KpiCard, Tabs, Spinner } from "@/components/ui";
import { getCitations, getSourceDomains, getSourceGaps, CitationItem } from "@/lib/api";

export default function SourcesPage() {
  const { token } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("domains");
  const [domains, setDomains] = useState<{ domain: string; total_citations: number }[]>([]);
  const [citations, setCitations] = useState<CitationItem[]>([]);
  const [gaps, setGaps] = useState<any[]>([]);
  const [citationTotal, setCitationTotal] = useState(0);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token]);

  async function loadData() {
    setLoading(true);
    try {
      const [domRes, citRes, gapRes] = await Promise.all([
        getSourceDomains(token!),
        getCitations(token!, undefined, 50),
        getSourceGaps(token!),
      ]);
      setDomains(domRes.items);
      setCitations(citRes.items);
      setCitationTotal(citRes.total);
      setGaps(gapRes.items);
    } catch (e: any) {
      const msg = e?.message || "";
      if (!msg.includes("No active project") && !msg.includes("Not Found") && !msg.includes("404")) {
        toast.error("Failed to load source data", msg);
      }
    }
    setLoading(false);
  }

  if (loading) return <div style={{ textAlign: "center", padding: 60 }}><Spinner size="lg" /></div>;

  const hasCitations = citations.length > 0 || domains.length > 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 className="page-title">Source Intelligence</h2>
        <p className="text-muted">Understand which domains and URLs AI models cite when responding to prompts about your category.</p>
      </div>

      <div className="data-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 32 }}>
        <KpiCard label="Unique Domains Cited" value={domains.length} />
        <KpiCard label="Total Citations" value={citationTotal} />
        <KpiCard label="Source Gaps Found" value={gaps.length} />
      </div>

      <Tabs
        tabs={[
          { key: "domains", label: "Top Domains", count: domains.length },
          { key: "citations", label: "All Citations", count: citationTotal },
          { key: "gaps", label: "Source Gaps", count: gaps.length },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      <div style={{ marginTop: 20 }}>
        {activeTab === "domains" && (
          domains.length === 0 ? (
            <EmptyState icon="🔗" title="No domains tracked yet" description="Run a prompt set on the AI Visibility page first. We'll extract all cited sources automatically." />
          ) : (
            <div className="table-list">
              <table style={{ width: "100%" }}>
                <thead><tr><th>#</th><th>Domain</th><th>Total Citations</th><th>Influence</th></tr></thead>
                <tbody>
                  {domains.map((d, i) => (
                    <tr key={d.domain}>
                      <td>{i + 1}</td>
                      <td><strong>{d.domain}</strong></td>
                      <td>{d.total_citations}</td>
                      <td>
                        <div className="progress-bar" style={{ width: 120 }}>
                          <div className="progress-bar-fill" style={{ width: `${Math.min((d.total_citations / (domains[0]?.total_citations || 1)) * 100, 100)}%` }} />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {activeTab === "citations" && (
          citations.length === 0 ? (
            <EmptyState icon="📝" title="No citations found yet" description="Citations are extracted from AI model responses when you run prompt sets." />
          ) : (
            <div className="table-list">
              <table style={{ width: "100%" }}>
                <thead><tr><th>URL</th><th>Domain</th><th>Type</th><th>First Seen</th></tr></thead>
                <tbody>
                  {citations.map(c => (
                    <tr key={c.id}>
                      <td style={{ maxWidth: 400, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        <a href={c.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--blue)" }}>{c.url}</a>
                      </td>
                      <td>{c.domain}</td>
                      <td><span className="badge">{c.content_type || "—"}</span></td>
                      <td className="text-muted">{c.first_seen_at ? new Date(c.first_seen_at).toLocaleDateString() : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {activeTab === "gaps" && (
          gaps.length === 0 ? (
            <EmptyState icon="🔍" title="No source gaps detected" description="Source gaps show where competitors are cited by AI but your brand is not. Run visibility tracking to discover gaps." />
          ) : (
            <div className="item-list">
              {gaps.map(g => (
                <div key={g.id} className="list-row">
                  <div>
                    <strong>{g.competitor_name}</strong> is cited on <strong>{g.domain}</strong>
                    <span className="badge badge-warning" style={{ marginLeft: 8 }}>{g.citation_count} citation{g.citation_count !== 1 ? "s" : ""}</span>
                  </div>
                  <p className="text-muted" style={{ marginTop: 4 }}>Your brand is not cited on this domain. Consider creating content there.</p>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  );
}
