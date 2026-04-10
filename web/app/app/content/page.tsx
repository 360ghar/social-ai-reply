"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Loader2,
  MessageSquare,
  FileEdit,
  CheckCircle,
  MoreHorizontal,
  Copy,
  Pencil,
  ExternalLink,
  ChevronDown,
  ArrowRight,
  LayoutTemplate,
} from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";
import { Button } from "@/components/ui/button";
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
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import { type PostDraft, apiRequest } from "@/lib/api";
import { withProjectId } from "@/lib/project";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PlatformIcon } from "@/components/shared/platform-icon";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { SheetPanel } from "@/components/shared/sheet-panel";
import { ScoreBadge } from "@/components/shared/score-badge";
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
  score?: number;
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
  const router = useRouter();
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

  const [threadOpen, setThreadOpen] = useState(true);
  const [rationaleOpen, setRationaleOpen] = useState(false);

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
    } catch (err: unknown) {
      error("Could not post to Reddit", getErrorMessage(err));
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
    } catch (err: unknown) {
      error("Could not generate post draft", getErrorMessage(err));
    }
    setGeneratingPost(false);
  }

  function openReplyDraft(draft: ReplyDraftRow) {
    setSelectedPost(null);
    setSelectedReply(draft);
    setReplyContent(draft.content);
    setThreadOpen(true);
    setRationaleOpen(false);
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
    } catch (err: unknown) {
      error("Could not save reply draft", getErrorMessage(err));
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
    } catch (err: unknown) {
      error("Could not save post draft", getErrorMessage(err));
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
    } catch (err: unknown) {
      error("Could not update status", getErrorMessage(err));
    }
  }

  const totalPublished = postedDrafts.length + publishedPosts.length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Content Studio"
        description="Manage reply drafts, original posts, and published activity from one workflow."
        actions={
          <Button onClick={generatePostDraft} disabled={generatingPost || !project}>
            {generatingPost && <Loader2 className="h-4 w-4 animate-spin" />}
            New Original Post
          </Button>
        }
        tabs={
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
                {totalPublished > 0 && (
                  <Badge variant="secondary" className="ml-1.5">{totalPublished}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />

      {loading && <p className="text-sm text-muted-foreground">Loading studio content...</p>}

      {/* Tabs Content Wrapper */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        {/* Replies Tab */}
        {!loading && (
          <TabsContent value="replies">
          {drafts.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No reply drafts yet"
              description="Generate response drafts from Engagement Radar. They will appear here for review, revision, and manual publishing."
              action={{
                label: "Open Engagement Radar",
                onClick: () => router.push("/app/discovery"),
              }}
            />
          ) : (
            <div className="space-y-2">
              {drafts.map((draft) => (
                <Card
                  key={draft.id}
                  className="cursor-pointer transition-colors hover:bg-accent/50"
                  onClick={() => openReplyDraft(draft)}
                >
                  <CardContent className="flex items-center gap-4 py-3">
                    {/* Left section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      {draft.opportunity_subreddit && (
                        <Badge variant="outline">r/{draft.opportunity_subreddit}</Badge>
                      )}
                      <Badge variant="secondary">v{draft.version}</Badge>
                    </div>

                    {/* Center section */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {draft.opportunity_title || "Reply Draft"}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.content.substring(0, 100)}{draft.content.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    {/* Right section */}
                    <div className="flex items-center gap-2 shrink-0">
                      {draft.score != null && <ScoreBadge score={draft.score} />}
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={
                            <Button variant="ghost" size="icon-xs">
                              <MoreHorizontal />
                            </Button>
                          }
                          onClick={(e: React.MouseEvent) => e.stopPropagation()}
                        />
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              copyToClipboard(draft.content);
                            }}
                          >
                            <Copy /> Copy
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              openReplyDraft(draft);
                            }}
                          >
                            <Pencil /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e: React.MouseEvent) => {
                              e.stopPropagation();
                              void markAsPosted(draft.opportunity_id);
                            }}
                          >
                            <CheckCircle /> Mark as Posted
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Posts Tab */}
      {!loading && (
        <TabsContent value="posts">
          {postDrafts.length === 0 ? (
            <EmptyState
              icon={FileEdit}
              title="No original post drafts yet"
              description="Use the studio to draft community-native posts inspired by Quora-style answers, Reddit posts, or educational updates."
              action={{
                label: "Generate First Post",
                onClick: generatePostDraft,
              }}
            />
          ) : (
            <div className="space-y-2">
              {postDrafts.map((draft) => (
                <Card
                  key={draft.id}
                  className="cursor-pointer transition-colors hover:bg-accent/50"
                  onClick={() => openPostDraft(draft)}
                >
                  <CardContent className="flex items-center gap-4 py-3">
                    {/* Left section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <Badge variant="secondary">Original Post</Badge>
                      <Badge variant="outline">v{draft.version}</Badge>
                    </div>

                    {/* Center section */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{draft.title}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.body.substring(0, 100)}{draft.body.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    {/* Right section */}
                    <div className="flex items-center gap-2 shrink-0">
                      <Button
                        variant="ghost"
                        size="xs"
                        onClick={(event) => {
                          event.stopPropagation();
                          copyToClipboard(`${draft.title}\n\n${draft.body}`);
                        }}
                      >
                        <Copy className="h-3 w-3" /> Copy
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
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Published Tab */}
      {!loading && (
        <TabsContent value="published">
          {postedDrafts.length === 0 && publishedPosts.length === 0 ? (
            <EmptyState
              icon={CheckCircle}
              title="No published content yet"
              description="Your published replies and posts will appear here."
            />
          ) : (
            <div className="space-y-2">
              {postedDrafts.map((draft) => (
                <Card key={`reply-${draft.id}`}>
                  <CardContent className="flex items-center gap-4 py-3">
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <StatusBadge variant="success">Posted</StatusBadge>
                      {draft.opportunity_subreddit && (
                        <Badge variant="outline">r/{draft.opportunity_subreddit}</Badge>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {draft.opportunity_title || "Published Reply"}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {draft.content.substring(0, 100)}{draft.content.length > 100 ? "..." : ""}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {draft.permalink && (
                        <a
                          href={redditUrl(draft.permalink)}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button variant="outline" size="xs">
                            <ExternalLink className="h-3 w-3" /> View Thread
                          </Button>
                        </a>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
              {publishedPosts.map((post) => (
                <Card key={`post-${post.id}`}>
                  <CardContent className="flex items-center gap-4 py-3">
                    <div className="flex items-center gap-2 shrink-0">
                      <PlatformIcon platform="reddit" />
                      <StatusBadge variant="success">{post.status}</StatusBadge>
                      <Badge variant="outline">r/{post.subreddit}</Badge>
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">Original Post</p>
                      <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
                        <span>{new Date(post.post_date).toLocaleDateString()}</span>
                        {post.upvotes !== undefined && <span>{post.upvotes} upvotes</span>}
                        {post.comments !== undefined && <span>{post.comments} comments</span>}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {post.permalink && (
                        <a href={redditUrl(post.permalink)} target="_blank" rel="noopener noreferrer">
                          <Button variant="outline" size="xs">
                            <ExternalLink className="h-3 w-3" /> View on Reddit
                          </Button>
                        </a>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      )}

      {/* Templates Tab */}
      {!loading && (
        <TabsContent value="templates">
          <Card>
            <CardContent className="flex items-center gap-4 py-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-muted shrink-0">
                <LayoutTemplate className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">Prompt Templates</p>
                <p className="text-xs text-muted-foreground">
                  Manage your prompt templates for reply and post generation.
                </p>
              </div>
              <Link href="/app/prompts">
                <Button variant="outline" size="sm">
                  Open Templates <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>
        )}
      </Tabs>

      {/* Reply Draft SheetPanel */}
      <SheetPanel
        title="Reply Draft"
        description="Review and edit your reply before publishing."
        open={!!selectedReply}
        onOpenChange={(open) => !open && setSelectedReply(null)}
        width="lg"
        footer={
          <div className="flex gap-2 w-full">
            <Button onClick={() => void saveReplyDraft()} disabled={savingReply} className="flex-1">
              {savingReply && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(replyContent)}>
              <Copy className="h-3.5 w-3.5" /> Copy
            </Button>
            {selectedReply?.permalink && (
              <Button
                variant="outline"
                onClick={() => copyAndOpenReddit(replyContent, selectedReply.permalink || "")}
              >
                Copy &amp; Open Reddit
              </Button>
            )}
            {selectedReply && (
              <Button variant="outline" onClick={() => void markAsPosted(selectedReply.opportunity_id)}>
                <CheckCircle className="h-3.5 w-3.5" /> Mark as Posted
              </Button>
            )}
          </div>
        }
      >
        {selectedReply && (
          <div className="space-y-4">
            {/* Original thread collapsible */}
            {selectedReply.permalink && (
              <Collapsible open={threadOpen} onOpenChange={setThreadOpen}>
                <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium w-full">
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform",
                      !threadOpen && "-rotate-90"
                    )}
                  />
                  Original Thread
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="rounded-lg bg-muted p-3">
                    <a
                      href={redditUrl(selectedReply.permalink)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-primary hover:underline inline-flex items-center gap-1"
                    >
                      View on Reddit <ExternalLink className="h-3 w-3" />
                    </a>
                    {selectedReply.body_excerpt && (
                      <p className="mt-2 text-xs text-muted-foreground leading-snug">
                        {selectedReply.body_excerpt.substring(0, 220)}...
                      </p>
                    )}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}

            {/* Reply content */}
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

            {/* Rationale collapsible */}
            {selectedReply.rationale && (
              <Collapsible open={rationaleOpen} onOpenChange={setRationaleOpen}>
                <CollapsibleTrigger className="flex items-center gap-1.5 text-sm font-medium w-full">
                  <ChevronDown
                    className={cn(
                      "h-4 w-4 transition-transform",
                      !rationaleOpen && "-rotate-90"
                    )}
                  />
                  Why this response works
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm text-muted-foreground">{selectedReply.rationale}</p>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        )}
      </SheetPanel>

      {/* Post Draft SheetPanel */}
      <SheetPanel
        title="Original Post Draft"
        description="Edit and manage your original post draft."
        open={!!selectedPost}
        onOpenChange={(open) => !open && setSelectedPost(null)}
        width="lg"
        footer={
          <div className="flex gap-2 w-full">
            <Button onClick={() => void savePostDraft()} disabled={savingPost} className="flex-1">
              {savingPost && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={() => copyToClipboard(`${postTitle}\n\n${postBody}`)}>
              <Copy className="h-3.5 w-3.5" /> Copy
            </Button>
            <Button
              onClick={() => {
                setPostingDraftId(selectedPost?.id || null);
                setShowPostConfirm(true);
              }}
            >
              Post to Reddit
            </Button>
          </div>
        }
      >
        {selectedPost && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Title</Label>
              <Input
                type="text"
                value={postTitle}
                onChange={(event) => setPostTitle(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Post Body</Label>
              <Textarea
                rows={14}
                value={postBody}
                onChange={(event) => setPostBody(event.target.value)}
                className="text-sm leading-relaxed"
              />
              <p className="text-xs text-muted-foreground">{postBody.length} characters</p>
            </div>
            {selectedPost.rationale && (
              <div className="rounded-lg bg-muted p-4">
                <h4 className="text-sm font-medium">Why this post works</h4>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedPost.rationale || "Educational, useful, and structured for community-native publishing."}
                </p>
              </div>
            )}
          </div>
        )}
      </SheetPanel>

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
