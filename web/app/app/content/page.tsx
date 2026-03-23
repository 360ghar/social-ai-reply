"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, EmptyState, Tabs, ScoreBadge, PlatformIcon, Drawer } from "@/components/ui";
import { ConfirmModal } from "@/components/modal";
import { apiRequest } from "@/lib/api";

interface Draft {
  id: number;
  opportunity_id: number;
  content: string;
  rationale: string;
  version: number;
  created_at: string;
  opportunity_title?: string;
  opportunity_subreddit?: string;
  permalink?: string;
  body_excerpt?: string;
}

export default function ContentPage() {
  const { token } = useAuth();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("drafts");
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [postedDrafts, setPostedDrafts] = useState<Draft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<Draft | null>(null);
  const [editContent, setEditContent] = useState("");

  useEffect(() => {
    if (!token) return;
    loadDrafts();
  }, [token]);

  async function loadDrafts() {
    setLoading(true);
    try {
      const [draftingRes, postedRes] = await Promise.allSettled([
        apiRequest<Draft[]>("/v1/drafts/replies?status=DRAFTING", {}, token),
        apiRequest<Draft[]>("/v1/drafts/replies?status=POSTED", {}, token),
      ]);
      setDrafts(draftingRes.status === "fulfilled" ? draftingRes.value : []);
      setPostedDrafts(postedRes.status === "fulfilled" ? postedRes.value : []);
    } catch (e: any) {
      setDrafts([]);
      setPostedDrafts([]);
    }
    setLoading(false);
  }

  function openDraft(d: Draft) {
    setSelectedDraft(d);
    setEditContent(d.content);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  }

  function redditUrl(permalink: string) {
    if (permalink.startsWith("http")) return permalink;
    return `https://www.reddit.com${permalink}`;
  }

  function copyAndOpenReddit(text: string, permalink: string) {
    navigator.clipboard.writeText(text);
    window.open(redditUrl(permalink), "_blank");
    toast.success("Reply copied! Reddit is opening — paste your reply there.");
  }

  async function markAsPosted(oppId: number) {
    try {
      await apiRequest(`/v1/opportunities/${oppId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: "POSTED" }),
      }, token);
      toast.success("Marked as posted!");
      setSelectedDraft(null);
      loadDrafts();
    } catch (e: any) {
      toast.error("Could not update status", e.message);
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h2 className="page-title">Content Studio</h2>
        <p className="text-muted">Manage all your AI-generated drafts, review content, and track what's been posted.</p>
      </div>

      <Tabs
        tabs={[
          { key: "drafts", label: "Drafts", count: drafts.length },
          { key: "posted", label: "Posted", count: postedDrafts.length },
          { key: "templates", label: "Templates" },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      <div style={{ marginTop: 20 }}>
        {activeTab === "drafts" && (
          drafts.length === 0 ? (
            <EmptyState
              icon="✍️"
              title="No drafts yet"
              description="Generate reply drafts from the Opportunities page. They'll appear here for editing and review."
              action={<Link href="/app/discovery" className="primary-button" style={{ textDecoration: "none" }}>Go to Opportunities</Link>}
            />
          ) : (
            <div className="item-list">
              {drafts.map(d => (
                <div key={d.id} className="list-row" style={{ cursor: "pointer" }} onClick={() => openDraft(d)}>
                  <div className="flex justify-between items-center">
                    <div>
                      <PlatformIcon platform="reddit" />
                      <strong style={{ marginLeft: 8 }}>{d.opportunity_title || "Reply Draft"}</strong>
                      {d.opportunity_subreddit && <span className="badge" style={{ marginLeft: 8 }}>r/{d.opportunity_subreddit}</span>}
                    </div>
                    <div className="flex gap-sm items-center">
                      <span className="text-muted" style={{ fontSize: 12 }}>v{d.version}</span>
                      <button className="ghost-button" onClick={(e) => { e.stopPropagation(); copyToClipboard(d.content); }}>📋 Copy</button>
                    </div>
                  </div>
                  <p className="text-muted" style={{ marginTop: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {d.content.substring(0, 150)}...
                  </p>
                </div>
              ))}
            </div>
          )
        )}

        {activeTab === "posted" && (
          postedDrafts.length === 0 ? (
            <EmptyState icon="📤" title="No posted content yet" description="Content will appear here after you mark drafts as posted." />
          ) : (
            <div className="item-list">
              {postedDrafts.map(d => (
                <div key={d.id} className="list-row" style={{ padding: 12 }}>
                  <div className="flex justify-between items-center">
                    <div>
                      <PlatformIcon platform="reddit" />
                      <strong style={{ marginLeft: 8 }}>{d.opportunity_title || "Reply"}</strong>
                      {d.opportunity_subreddit && <span className="badge" style={{ marginLeft: 8 }}>r/{d.opportunity_subreddit}</span>}
                    </div>
                    <div className="flex gap-sm items-center">
                      <span className="badge" style={{ background: "var(--green-bg, #e6f9e6)", color: "var(--green, #16a34a)" }}>Posted</span>
                      {d.permalink && (
                        <a href={redditUrl(d.permalink || "")} target="_blank" rel="noopener noreferrer" className="ghost-button" style={{ textDecoration: "none" }}>
                          🔗 View
                        </a>
                      )}
                    </div>
                  </div>
                  <p className="text-muted" style={{ marginTop: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {d.content.substring(0, 150)}...
                  </p>
                </div>
              ))}
            </div>
          )
        )}

        {activeTab === "templates" && (
          <EmptyState
            icon="📋"
            title="Prompt Templates"
            description="Customize how AI generates your content."
            action={<Link href="/app/prompts" className="primary-button" style={{ textDecoration: "none" }}>Manage Templates</Link>}
          />
        )}
      </div>

      {/* Draft Detail Drawer */}
      <Drawer open={!!selectedDraft} onClose={() => setSelectedDraft(null)} title="Edit Draft"
        footer={
          <div className="flex gap-md" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
            <button className="secondary-button" onClick={() => copyToClipboard(editContent)}>📋 Copy</button>
            {selectedDraft?.permalink && (
              <Button
                variant="primary"
                onClick={() => copyAndOpenReddit(editContent, selectedDraft.permalink!)}
              >
                📋 Copy &amp; Open on Reddit
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => {
                if (selectedDraft) markAsPosted(selectedDraft.opportunity_id);
              }}
            >
              ✅ Mark as Posted
            </Button>
          </div>
        }
      >
        {selectedDraft && (
          <>
            {/* Link to original Reddit post */}
            {selectedDraft.permalink && (
              <div style={{ marginBottom: 16, padding: 12, background: "var(--surface)", borderRadius: 8 }}>
                <a
                  href={redditUrl(selectedDraft.permalink)}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--accent)", fontWeight: 500, fontSize: 13, textDecoration: "none" }}
                >
                  🔗 View original post on Reddit →
                </a>
                {selectedDraft.body_excerpt && (
                  <p className="text-muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.4 }}>
                    {selectedDraft.body_excerpt.substring(0, 200)}...
                  </p>
                )}
              </div>
            )}

            <div className="field">
              <label className="field-label">Reply Content</label>
              <textarea
                rows={12}
                value={editContent}
                onChange={e => setEditContent(e.target.value)}
                style={{ fontFamily: "monospace", fontSize: 13 }}
              />
              <p className="field-help">{editContent.length} characters</p>
            </div>
            <div className="card" style={{ backgroundColor: "var(--surface)", marginTop: 16 }}>
              <h4 className="field-label">Why this reply works:</h4>
              <p className="text-muted" style={{ fontSize: 13 }}>{selectedDraft.rationale}</p>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
}
