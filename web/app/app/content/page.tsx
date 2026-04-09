"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button, buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
  SheetDescription,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { type PostDraft, apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PlatformIcon } from "@/components/shared/platform-icon";
import { redditUrl, copyText } from "@/lib/reddit";

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

interface RedditAccount {
  id: number;
  username: string;
}

interface PublishedPost {
  id: number;
  content: string;
  subreddit: string;
  post_date: string;
  status: string;
  permalink?: string;
  upvotes?: number;
  comments?: number;
}

export default function ContentPage() {
  const { token } = useAuth();
  const { success, error } = useToast();
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

  const [publishedPosts, setPublishedPosts] = useState<PublishedPost[]>([]);
  const [redditAccounts, setRedditAccounts] = useState<RedditAccount[]>([]);
  const [postingReddit, setPostingReddit] = useState(false);
  const [showPostConfirm, setShowPostConfirm] = useState(false);
  const [postingDraftId, setPostingDraftId] = useState<number | null>(null);

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadDrafts();
  }, [token, selectedProjectId]);

  async function loadDrafts() {
    setLoading(true);
    try {
      const [dashboardRes, draftingRes, postedRes, postsRes, accountsRes, publishedRes] = await Promise.allSettled([
        apiRequest<any>(withProjectId("/v1/dashboard", selectedProjectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=drafting", selectedProjectId), {}, token),
        apiRequest<ReplyDraftRow[]>(withProjectId("/v1/drafts/replies?status=posted", selectedProjectId), {}, token),
        apiRequest<PostDraft[]>(withProjectId("/v1/drafts/posts", selectedProjectId), {}, token),
        apiRequest<RedditAccount[]>(`/v1/reddit/accounts?workspace_id=${selectedProjectId}`, {}, token),
        apiRequest<PublishedPost[]>(withProjectId("/v1/reddit/published", selectedProjectId), {}, token),
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
      setRedditAccounts(accountsRes.status === "fulfilled" ? accountsRes.value : []);
      setPublishedPosts(publishedRes.status === "fulfilled" ? publishedRes.value : []);
    } catch (err) {
      setDrafts([]);
      setPostedDrafts([]);
      setPostDrafts([]);
      setRedditAccounts([]);
      setPublishedPosts([]);
    }
    setLoading(false);
  }

  async function postToReddit(draftId: number) {
    if (!project) return;
    setPostingReddit(true);
    try {
      const draft = postDrafts.find((d) => d.id === draftId);
      if (!draft) return;

      await apiRequest("/v1/reddit/post", {
        method: "POST",
        body: JSON.stringify({
          type: "post",
          project_id: project.id,
          content: `${draft.title}\n\n${draft.body}`,
          draft_id: draftId,
        }),
      }, token);

      success("Posted to Reddit", "Your post has been published");
      setPostDrafts((rows) => rows.map((r) => (r.id === draftId ? { ...r, status: "posted" } : r)));
      setShowPostConfirm(false);
      await loadDrafts();
    } catch (err: any) {
      error("Could not post to Reddit", err.message);
    }
    setPostingReddit(false);
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
      success("Original post drafted");
      setPostDrafts((rows) => [draft, ...rows]);
      openPostDraft(draft);
      setActiveTab("posts");
    } catch (err: any) {
      error("Could not generate post draft", err.message);
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

  async function copyToClipboard(text: string) {
    try {
      await copyText(text);
      success("Copied to clipboard");
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
    }
  }

  async function copyAndOpenReddit(text: string, permalink: string) {
    try {
      await copyText(text);
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
      return;
    }
    window.open(redditUrl(permalink), "_blank");
    success("Draft copied. Reddit is opening so you can review and paste.");
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
      success("Reply draft saved");
    } catch (err: any) {
      error("Could not save reply draft", err.message);
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
      success("Post draft saved");
    } catch (err: any) {
      error("Could not save post draft", err.message);
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
      success("Marked as posted");
      setSelectedReply(null);
      await loadDrafts();
    } catch (err: any) {
      error("Could not update status", err.message);
    }
  }

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Publishing Workspace</p>
          <h2 className="text-2xl font-semibold tracking-tight">Content Studio</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage reply drafts, original posts, and published activity from one workflow instead of treating every community interaction as a one-off Reddit action.
          </p>
        </div>
        <Button onClick={generatePostDraft} disabled={generatingPost || !project}>
          {generatingPost && <Loader2 className="h-4 w-4 animate-spin" />}
          New Original Post
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="replies">
            Reply Queue
            {drafts.length > 0 && (
              <Badge variant="secondary" className="ml-1.5">{drafts.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="posts">
            Original Posts
            {postDrafts.length > 0 && (
              <Badge variant="secondary" className="ml-1.5">{postDrafts.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="published">
            Published
            {(postedDrafts.length + publishedPosts.length) > 0 && (
              <Badge variant="secondary" className="ml-1.5">{postedDrafts.length + publishedPosts.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        {loading && <p className="text-sm text-muted-foreground">Loading studio content...</p>}

        {/* Replies Tab */}
        {!loading && (
          <TabsContent value="replies">
            {drafts.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <div className="text-4xl">REP</div>
                <h3 className="mt-4 text-lg font-medium">No reply drafts yet</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Generate response drafts from Engagement Radar. They will appear here for review, revision, and manual publishing.
                </p>
                <Link href="/app/discovery" className={cn(buttonVariants({ variant: "outline" }), "mt-4")}>
                  Open Engagement Radar
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {drafts.map((draft) => (
                  <div
                    key={draft.id}
                    className="rounded-lg border bg-card p-4 cursor-pointer hover:bg-accent/50 transition-colors"
                    onClick={() => openReplyDraft(draft)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <PlatformIcon platform="reddit" />
                          <Badge variant="secondary">Reply</Badge>
                          {draft.opportunity_subreddit && <Badge variant="outline">r/{draft.opportunity_subreddit}</Badge>}
                        </div>
                        <strong className="mt-2.5 block">{draft.opportunity_title || "Reply Draft"}</strong>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">v{draft.version}</span>
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            copyToClipboard(draft.content);
                          }}
                        >
                          Copy
                        </Button>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {draft.content.substring(0, 170)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        )}

        {/* Posts Tab */}
        {!loading && (
          <TabsContent value="posts">
            {postDrafts.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <div className="text-4xl">PST</div>
                <h3 className="mt-4 text-lg font-medium">No original post drafts yet</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  Use the studio to draft community-native posts inspired by Quora-style answers, Reddit posts, or educational updates.
                </p>
                <Button
                  className="mt-4"
                  onClick={generatePostDraft}
                  disabled={generatingPost || !project}
                >
                  {generatingPost && <Loader2 className="h-4 w-4 animate-spin" />}
                  Generate First Post
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {postDrafts.map((draft) => (
                  <div key={draft.id} className="rounded-lg border bg-card p-4">
                    <div className="flex items-center justify-between cursor-pointer" onClick={() => openPostDraft(draft)}>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">Original Post</Badge>
                          <Badge variant="outline">v{draft.version}</Badge>
                        </div>
                        <strong className="mt-2.5 block">{draft.title}</strong>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-4">
                        <Button
                          variant="ghost"
                          size="xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            copyToClipboard(`${draft.title}\n\n${draft.body}`);
                          }}
                        >
                          Copy
                        </Button>
                        <Button
                          size="xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            setPostingDraftId(draft.id);
                            setShowPostConfirm(true);
                          }}
                        >
                          Post to Reddit
                        </Button>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {draft.body.substring(0, 170)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        )}

        {/* Published Tab */}
        {!loading && (
          <TabsContent value="published">
            {postedDrafts.length === 0 && publishedPosts.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <div className="text-4xl">PUB</div>
                <h3 className="mt-4 text-lg font-medium">No published content yet</h3>
                <p className="mt-2 text-sm text-muted-foreground">Your published replies and posts will appear here.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {postedDrafts.map((draft) => (
                  <div key={`reply-${draft.id}`} className="rounded-lg border bg-card p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <PlatformIcon platform="reddit" />
                          <Badge variant="default" className="bg-emerald-600 text-white">Posted</Badge>
                          {draft.opportunity_subreddit && <Badge variant="outline">r/{draft.opportunity_subreddit}</Badge>}
                        </div>
                        <strong className="mt-2.5 block">{draft.opportunity_title || "Published Reply"}</strong>
                      </div>
                      {draft.permalink && (
                        <a href={redditUrl(draft.permalink)} target="_blank" rel="noopener noreferrer">
                          <Button variant="ghost" size="xs">View Thread</Button>
                        </a>
                      )}
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {draft.content.substring(0, 170)}...
                    </p>
                  </div>
                ))}
                {publishedPosts.map((post) => (
                  <div key={`post-${post.id}`} className="rounded-lg border bg-card p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <PlatformIcon platform="reddit" />
                          <Badge variant="default" className="bg-emerald-600 text-white">{post.status}</Badge>
                          <Badge variant="outline">r/{post.subreddit}</Badge>
                        </div>
                        <strong className="mt-2.5 block">Original Post</strong>
                      </div>
                      {post.permalink && (
                        <a href={post.permalink} target="_blank" rel="noopener noreferrer">
                          <Button variant="ghost" size="xs">View Post</Button>
                        </a>
                      )}
                    </div>
                    <div className="mt-2 flex gap-3 text-xs text-muted-foreground">
                      <span>Posted: {new Date(post.post_date).toLocaleDateString()}</span>
                      {post.upvotes !== undefined && <span>Upvotes: {post.upvotes}</span>}
                      {post.comments !== undefined && <span>Comments: {post.comments}</span>}
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {post.content.substring(0, 170)}...
                    </p>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        )}

        {/* Templates Tab */}
        {!loading && (
          <TabsContent value="templates">
            <div className="flex flex-col items-center justify-center p-8 text-center">
              <div className="text-4xl">TPL</div>
              <h3 className="mt-4 text-lg font-medium">Prompt Templates</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Manage reply, post, and analysis prompt systems from a single template library.
              </p>
              <Link href="/app/prompts" className={cn(buttonVariants({ variant: "outline" }), "mt-4")}>
                Open Templates
              </Link>
            </div>
          </TabsContent>
        )}
      </Tabs>

      {/* Reply Draft Sheet */}
      <Sheet open={!!selectedReply} onOpenChange={(open) => !open && setSelectedReply(null)}>
        <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Reply Draft</SheetTitle>
            <SheetDescription>Review and edit your reply draft before publishing.</SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-4">
            {selectedReply?.permalink && (
              <div className="mb-4 rounded-lg bg-muted p-3">
                <a
                  href={redditUrl(selectedReply.permalink)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-primary hover:underline"
                >
                  View original Reddit thread {"->"}
                </a>
                {selectedReply.body_excerpt && (
                  <p className="mt-2 text-xs text-muted-foreground leading-snug">
                    {selectedReply.body_excerpt.substring(0, 220)}...
                  </p>
                )}
              </div>
            )}
            <div className="space-y-2">
              <Label>Reply Content</Label>
              <Textarea
                rows={12}
                value={replyContent}
                onChange={(event) => setReplyContent(event.target.value)}
                className="text-sm leading-relaxed"
              />
              <p className="text-xs text-muted-foreground">{replyContent.length} characters</p>
            </div>
            <div className="mt-4 rounded-lg bg-muted p-4">
              <h4 className="text-sm font-medium">Why this response works</h4>
              <p className="mt-1 text-sm text-muted-foreground">{selectedReply?.rationale}</p>
            </div>
          </div>

          <SheetFooter className="flex-row flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={saveReplyDraft} disabled={savingReply}>
              {savingReply && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Draft
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(replyContent)}>
              Copy
            </Button>
            {selectedReply?.permalink && (
              <Button onClick={() => copyAndOpenReddit(replyContent, selectedReply.permalink || "")}>
                Copy and Open on Reddit
              </Button>
            )}
            {selectedReply && (
              <Button variant="outline" onClick={() => markAsPosted(selectedReply.opportunity_id)}>
                Mark as Posted
              </Button>
            )}
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Post Draft Sheet */}
      <Sheet open={!!selectedPost} onOpenChange={(open) => !open && setSelectedPost(null)}>
        <SheetContent side="right" className="sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Original Post Draft</SheetTitle>
            <SheetDescription>Edit and manage your original post draft.</SheetDescription>
          </SheetHeader>

          <div className="flex-1 overflow-y-auto px-4">
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                type="text"
                value={postTitle}
                onChange={(event) => setPostTitle(event.target.value)}
              />
            </div>
            <div className="mt-4 space-y-2">
              <Label>Post Body</Label>
              <Textarea
                rows={14}
                value={postBody}
                onChange={(event) => setPostBody(event.target.value)}
                className="text-sm leading-relaxed"
              />
              <p className="text-xs text-muted-foreground">{postBody.length} characters</p>
            </div>
            <div className="mt-4 rounded-lg bg-muted p-4">
              <h4 className="text-sm font-medium">Why this post works</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                {selectedPost?.rationale || "Educational, useful, and structured for community-native publishing."}
              </p>
            </div>
          </div>

          <SheetFooter className="flex-row flex-wrap justify-end gap-2">
            <Button variant="outline" onClick={savePostDraft} disabled={savingPost}>
              {savingPost && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Draft
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(`${postTitle}\n\n${postBody}`)}>
              Copy
            </Button>
            <Button
              onClick={() => {
                setPostingDraftId(selectedPost?.id || null);
                setShowPostConfirm(true);
              }}
            >
              Post to Reddit
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Post to Reddit Confirm Dialog */}
      <Dialog open={showPostConfirm} onOpenChange={setShowPostConfirm}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Post to Reddit</DialogTitle>
            <DialogDescription>Review your post before publishing to Reddit.</DialogDescription>
          </DialogHeader>
          {postingDraftId && postDrafts.find((d) => d.id === postingDraftId) && (
            <div className="space-y-4">
              <div className="rounded-lg bg-muted p-4">
                <strong className="block mb-2">
                  {postDrafts.find((d) => d.id === postingDraftId)?.title}
                </strong>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {postDrafts.find((d) => d.id === postingDraftId)?.body.substring(0, 200)}...
                </p>
              </div>
              <div className="space-y-2">
                <Label>Target Subreddit</Label>
                <Input type="text" placeholder="e.g., r/community" disabled className="opacity-60" />
              </div>
              <div className="rounded-lg bg-muted p-3">
                <Label>Connected Reddit Account</Label>
                <p className="mt-1.5 text-sm">
                  {redditAccounts.length > 0
                    ? `@${redditAccounts[0].username}`
                    : <a href="/app/settings" className="text-primary hover:underline">Connect Reddit Account</a>}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPostConfirm(false)}>
              Cancel
            </Button>
            <Button
              disabled={postingReddit || redditAccounts.length === 0}
              onClick={() => void postToReddit(postingDraftId!)}
            >
              {postingReddit && <Loader2 className="h-4 w-4 animate-spin" />}
              Post Now
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
