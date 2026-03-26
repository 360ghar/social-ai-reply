"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, Drawer, EmptyState, PlatformIcon, Tabs } from "@/components/ui";
import { type PostDraft, apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/lib/use-selected-project";

interface ReplyDraftRow {
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

interface ProjectContext {
  id: number;
  name: string;
}

export default function ContentPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();

  const [activeTab, setActiveTab] = useState("replies");
  const [drafts, setDrafts] = useState<ReplyDraftRow[]>([]);
  const [postedDrafts, setPostedDrafts] = useState<ReplyDraftRow[]>([]);
  const [postDrafts, setPostDrafts] = useState<PostDraft[]>([]);
  const [project, setProject] = useState<ProjectContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingPost, setGeneratingPost] = useState(false);
  const [savingReply, setSavingReply] = useState(false);
  const [savingPost, setSavingPost] = useState(false);

  const [selectedReply, setSelectedReply] = useState<ReplyDraftRow | null>(null);
  const [replyContent, setReplyContent] = useState("");

  const [selectedPost, setSelectedPost] = useState<PostDraft | null>(null);
  const [postTitle, setPostTitle] = useState("");
  const [postBody, setPostBody] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadDrafts();
  }, [token, selectedProjectId]);

  async function loadDrafts() {
    setLoading(true);
    try {
      const [dashboardRes, draftingRes, postedRes, postsRes] = await Promise.allSettled([
        apiRequest<any>(withProjectId("/v1/dashboard", selectedProjectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=drafting", selectedProjectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=posted", selectedProjectId), {}, token),
        apiRequest<PostDraft[]>(withProjectId("/v1/drafts/posts", selectedProjectId), {}, token),
      ]);

      if (dashboardRes.status === "fulfilled") {
        const focusProject =
          dashboardRes.value.projects?.find((item: ProjectContext) => item.id === selectedProjectId) ||
          dashboardRes.value.projects?.[0] ||
          null;
        setProject(focusProject ? { id: focusProject.id, name: focusProject.name } : null);
      }
      setDrafts(draftingRes.status === "fulfilled" ? draftingRes.value : []);
      setPostedDrafts(postedRes.status === "fulfilled" ? postedRes.value : []);
      setPostDrafts(postsRes.status === "fulfilled" ? postsRes.value : []);
    } catch (error) {
      setDrafts([]);
      setPostedDrafts([]);
      setPostDrafts([]);
    }
    setLoading(false);
  }

  async function generatePostDraft() {
    if (!project) {
      return;
    }
    setGeneratingPost(true);
    try {
      const draft = await apiRequest<PostDraft>(
        "/v1/drafts/posts",
        {
          method: "POST",
          body: JSON.stringify({ project_id: project.id }),
        },
        token
      );
      toast.success("Original post drafted");
      setPostDrafts((rows) => [draft, ...rows]);
      openPostDraft(draft);
      setActiveTab("posts");
    } catch (error: any) {
      toast.error("Could not generate post draft", error.message);
    }
    setGeneratingPost(false);
  }

  function openReplyDraft(draft: ReplyDraftRow) {
    setSelectedPost(null);
    setSelectedReply(draft);
    setReplyContent(draft.content);
  }

  function openPostDraft(draft: PostDraft) {
    setSelectedReply(null);
    setSelectedPost(draft);
    setPostTitle(draft.title);
    setPostBody(draft.body);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  }

  function redditUrl(permalink: string) {
    if (permalink.startsWith("http")) {
      return permalink;
    }
    return `https://www.reddit.com${permalink}`;
  }

  function copyAndOpenReddit(text: string, permalink: string) {
    navigator.clipboard.writeText(text);
    window.open(redditUrl(permalink), "_blank");
    toast.success("Draft copied. Reddit is opening so you can review and paste.");
  }

  async function saveReplyDraft() {
    if (!selectedReply) {
      return;
    }
    setSavingReply(true);
    try {
      const updated = await apiRequest<ReplyDraftRow>(
        `/v1/drafts/replies/${selectedReply.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            content: replyContent,
            rationale: selectedReply.rationale || null,
          }),
        },
        token
      );
      setDrafts((rows) => rows.map((row) => (row.id === updated.id ? { ...row, content: updated.content, rationale: updated.rationale || "" } : row)));
      setSelectedReply((current) => (current ? { ...current, content: updated.content, rationale: updated.rationale || "" } : current));
      toast.success("Reply draft saved");
    } catch (error: any) {
      toast.error("Could not save reply draft", error.message);
    }
    setSavingReply(false);
  }

  async function savePostDraft() {
    if (!selectedPost) {
      return;
    }
    setSavingPost(true);
    try {
      const updated = await apiRequest<PostDraft>(
        `/v1/drafts/posts/${selectedPost.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            title: postTitle,
            body: postBody,
            rationale: selectedPost.rationale,
          }),
        },
        token
      );
      setPostDrafts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setSelectedPost(updated);
      toast.success("Post draft saved");
    } catch (error: any) {
      toast.error("Could not save post draft", error.message);
    }
    setSavingPost(false);
  }

  async function markAsPosted(oppId: number) {
    try {
      await apiRequest(
        `/v1/opportunities/${oppId}/status`,
        {
          method: "PUT",
          body: JSON.stringify({ status: "posted" }),
        },
        token
      );
      toast.success("Marked as posted");
      setSelectedReply(null);
      await loadDrafts();
    } catch (error: any) {
      toast.error("Could not update status", error.message);
    }
  }

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <div className="flex justify-between items-center" style={{ gap: 16, flexWrap: "wrap" }}>
        <div>
          <div className="eyebrow">Publishing Workspace</div>
          <h2 className="page-title">Content Studio</h2>
          <p className="text-muted">
            Manage reply drafts, original posts, and published activity from one workflow instead of treating every community interaction as a one-off Reddit action.
          </p>
        </div>
        <Button onClick={generatePostDraft} loading={generatingPost} disabled={!project}>
          New Original Post
        </Button>
      </div>

      <Tabs
        tabs={[
          { key: "replies", label: "Reply Queue", count: drafts.length },
          { key: "posts", label: "Original Posts", count: postDrafts.length },
          { key: "published", label: "Published", count: postedDrafts.length },
          { key: "templates", label: "Templates" },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {loading && <p className="text-muted">Loading studio content...</p>}

      {!loading && activeTab === "replies" && (
        drafts.length === 0 ? (
          <EmptyState
            icon="REP"
            title="No reply drafts yet"
            description="Generate response drafts from Engagement Radar. They will appear here for review, revision, and manual publishing."
            action={<Link href="/app/discovery" className="primary-button" style={{ textDecoration: "none" }}>Open Engagement Radar</Link>}
          />
        ) : (
          <div className="item-list">
            {drafts.map((draft) => (
              <div key={draft.id} className="list-row" style={{ cursor: "pointer" }} onClick={() => openReplyDraft(draft)}>
                <div className="flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-sm">
                      <PlatformIcon platform="reddit" />
                      <span className="badge">Reply</span>
                      {draft.opportunity_subreddit && <span className="badge">r/{draft.opportunity_subreddit}</span>}
                    </div>
                    <strong style={{ display: "block", marginTop: 10 }}>{draft.opportunity_title || "Reply Draft"}</strong>
                  </div>
                  <div className="flex gap-sm items-center">
                    <span className="text-muted text-sm">v{draft.version}</span>
                    <button
                      className="ghost-button"
                      onClick={(event) => {
                        event.stopPropagation();
                        copyToClipboard(draft.content);
                      }}
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <p className="text-muted" style={{ marginTop: 8 }}>
                  {draft.content.substring(0, 170)}...
                </p>
              </div>
            ))}
          </div>
        )
      )}

      {!loading && activeTab === "posts" && (
        postDrafts.length === 0 ? (
          <EmptyState
            icon="PST"
            title="No original post drafts yet"
            description="Use the studio to draft community-native posts inspired by Quora-style answers, Reddit posts, or educational updates."
            action={<Button onClick={generatePostDraft} loading={generatingPost} disabled={!project}>Generate First Post</Button>}
          />
        ) : (
          <div className="item-list">
            {postDrafts.map((draft) => (
              <div key={draft.id} className="list-row" style={{ cursor: "pointer" }} onClick={() => openPostDraft(draft)}>
                <div className="flex justify-between items-center">
                  <div>
                    <div className="badge-row">
                      <span className="badge">Original Post</span>
                      <span className="badge">v{draft.version}</span>
                    </div>
                    <strong style={{ display: "block", marginTop: 10 }}>{draft.title}</strong>
                  </div>
                  <button
                    className="ghost-button"
                    onClick={(event) => {
                      event.stopPropagation();
                      copyToClipboard(`${draft.title}\n\n${draft.body}`);
                    }}
                  >
                    Copy
                  </button>
                </div>
                <p className="text-muted" style={{ marginTop: 8 }}>
                  {draft.body.substring(0, 170)}...
                </p>
              </div>
            ))}
          </div>
        )
      )}

      {!loading && activeTab === "published" && (
        postedDrafts.length === 0 ? (
          <EmptyState icon="PUB" title="No published replies yet" description="Published content will appear here after you mark a draft as posted." />
        ) : (
          <div className="item-list">
            {postedDrafts.map((draft) => (
              <div key={draft.id} className="list-row">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-sm">
                      <PlatformIcon platform="reddit" />
                      <span className="badge badge-success">Posted</span>
                      {draft.opportunity_subreddit && <span className="badge">r/{draft.opportunity_subreddit}</span>}
                    </div>
                    <strong style={{ display: "block", marginTop: 10 }}>{draft.opportunity_title || "Published Reply"}</strong>
                  </div>
                  {draft.permalink && (
                    <a href={redditUrl(draft.permalink)} target="_blank" rel="noopener noreferrer" className="ghost-button" style={{ textDecoration: "none" }}>
                      View Thread
                    </a>
                  )}
                </div>
                <p className="text-muted" style={{ marginTop: 8 }}>
                  {draft.content.substring(0, 170)}...
                </p>
              </div>
            ))}
          </div>
        )
      )}

      {!loading && activeTab === "templates" && (
        <EmptyState
          icon="TPL"
          title="Prompt Templates"
          description="Manage reply, post, and analysis prompt systems from a single template library."
          action={<Link href="/app/prompts" className="primary-button" style={{ textDecoration: "none" }}>Open Templates</Link>}
        />
      )}

      <Drawer
        open={!!selectedReply}
        onClose={() => setSelectedReply(null)}
        title="Reply Draft"
        footer={
          <div className="flex gap-md" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
            <Button variant="secondary" onClick={saveReplyDraft} loading={savingReply}>
              Save Draft
            </Button>
            <button className="secondary-button" onClick={() => copyToClipboard(replyContent)}>
              Copy
            </button>
            {selectedReply?.permalink && (
              <Button variant="primary" onClick={() => copyAndOpenReddit(replyContent, selectedReply.permalink || "")}>
                Copy and Open on Reddit
              </Button>
            )}
            {selectedReply && (
              <Button variant="secondary" onClick={() => markAsPosted(selectedReply.opportunity_id)}>
                Mark as Posted
              </Button>
            )}
          </div>
        }
      >
        {selectedReply && (
          <>
            {selectedReply.permalink && (
              <div style={{ marginBottom: 16, padding: 12, background: "var(--surface)", borderRadius: 8 }}>
                <a href={redditUrl(selectedReply.permalink)} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", fontWeight: 500, fontSize: 13 }}>
                  View original Reddit thread {"->"}
                </a>
                {selectedReply.body_excerpt && (
                  <p className="text-muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.4 }}>
                    {selectedReply.body_excerpt.substring(0, 220)}...
                  </p>
                )}
              </div>
            )}
            <div className="field">
              <label className="field-label">Reply Content</label>
              <textarea rows={12} value={replyContent} onChange={(event) => setReplyContent(event.target.value)} style={{ fontSize: 13, lineHeight: 1.5 }} />
              <p className="field-help">{replyContent.length} characters</p>
            </div>
            <div className="card" style={{ backgroundColor: "var(--surface)", marginTop: 16 }}>
              <h4 className="field-label">Why this response works</h4>
              <p className="text-muted" style={{ fontSize: 13 }}>{selectedReply.rationale}</p>
            </div>
          </>
        )}
      </Drawer>

      <Drawer
        open={!!selectedPost}
        onClose={() => setSelectedPost(null)}
        title="Original Post Draft"
        footer={
          <div className="flex gap-md" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
            <Button variant="secondary" onClick={savePostDraft} loading={savingPost}>
              Save Draft
            </Button>
            <button className="secondary-button" onClick={() => copyToClipboard(`${postTitle}\n\n${postBody}`)}>
              Copy
            </button>
          </div>
        }
      >
        {selectedPost && (
          <>
            <div className="field">
              <label className="field-label">Title</label>
              <input type="text" value={postTitle} onChange={(event) => setPostTitle(event.target.value)} />
            </div>
            <div className="field">
              <label className="field-label">Post Body</label>
              <textarea rows={14} value={postBody} onChange={(event) => setPostBody(event.target.value)} style={{ fontSize: 13, lineHeight: 1.6 }} />
              <p className="field-help">{postBody.length} characters</p>
            </div>
            <div className="card" style={{ backgroundColor: "var(--surface)", marginTop: 16 }}>
              <h4 className="field-label">Why this post works</h4>
              <p className="text-muted" style={{ fontSize: 13 }}>{selectedPost.rationale || "Educational, useful, and structured for community-native publishing."}</p>
            </div>
          </>
        )}
      </Drawer>
    </div>
  );
}
