"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowDown,
  ArrowUp,
  Copy,
  Download,
  Loader2,
  Megaphone,
  Plus,
  Send,
  Trash2,
} from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage, isApiError } from "@/types/errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PageHeader } from "@/components/shared/page-header";
import { cn } from "@/lib/utils";
import { copyText } from "@/lib/reddit";
import {
  publishAmplifyDraft,
  updateAmplifyDraft,
  type AmplifyDraft,
} from "@/lib/api/amplify";
import { loadAmplifyDrafts, rememberAmplifyDraft } from "@/lib/amplify-store";

const TWEET_MAX_CHARS = 280;
const LINKEDIN_MIN_IDEAL = 1300;
const LINKEDIN_MAX_IDEAL = 3000;

const articleBriefs = [
  { title: "How to Use AI for Reddit Outreach", keyword: "ai reddit outreach", outline: "1. Why Reddit matters\n2. Choosing subreddits\n3. Crafting replies..." },
  { title: "GEO vs SEO: What Changed", keyword: "generative engine optimization", outline: "1. Traditional SEO\n2. AI overviews\n3. Visibility tactics..." },
];

const xPosts = [
  { text: "Reddit isn't just for memes. It's where your ICP asks questions before they buy. Here's how to show up without being salesy.", type: "Thread starter" },
  { text: "The best marketing doesn't feel like marketing. It feels like a helpful reply at the right moment.", type: "Stand-alone" },
];

const linkedInPosts = [
  { text: "We analyzed 10,000 Reddit threads to find the #1 thing buyers complain about before switching tools. Spoiler: it's not price.", type: "Story" },
  { text: "3 signals that someone is in 'comparison mode' on Reddit — and how to reply without breaking community rules.", type: "Listicle" },
];

const ugcBriefs = [
  { hook: "POV: You finally found a tool that doesn't spam Reddit...", scenes: 4, duration: "45s" },
  { hook: "How I got 300 qualified leads from one Reddit comment.", scenes: 5, duration: "60s" },
];

function parsePositiveInt(value: string | null): number | null {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export default function ContentStudioPage() {
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const { success, error } = useToast();
  const requestedDraftId = parsePositiveInt(searchParams.get("amplifyDraft"));

  const [activeTab, setActiveTab] = useState("articles");
  const [amplifyDrafts, setAmplifyDrafts] = useState<AmplifyDraft[]>([]);
  const [selectedDraftId, setSelectedDraftId] = useState<number | null>(null);

  // Editor state for the selected amplified draft
  const [tweets, setTweets] = useState<string[]>([]);
  const [linkedinContent, setLinkedinContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    setAmplifyDrafts(loadAmplifyDrafts());
    if (requestedDraftId) {
      setSelectedDraftId(requestedDraftId);
      setActiveTab("amplified");
    }
  }, [requestedDraftId]);

  const selectedDraft = amplifyDrafts.find((d) => d.id === selectedDraftId) ?? null;

  // Re-seed the editor whenever the selected draft changes.
  useEffect(() => {
    if (!selectedDraft) {
      setTweets([]);
      setLinkedinContent("");
      return;
    }
    if (selectedDraft.platform === "x") {
      setTweets(selectedDraft.thread_json.length > 0 ? selectedDraft.thread_json : [""]);
    } else {
      setLinkedinContent(selectedDraft.content ?? selectedDraft.thread_json.join("\n\n"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDraft?.id]);

  function applyUpdatedDraft(updated: AmplifyDraft) {
    rememberAmplifyDraft(updated);
    setAmplifyDrafts((rows) => {
      const exists = rows.some((row) => row.id === updated.id);
      return exists ? rows.map((row) => (row.id === updated.id ? updated : row)) : [updated, ...rows];
    });
  }

  function updateTweet(index: number, value: string) {
    setTweets((rows) => rows.map((tweet, i) => (i === index ? value : tweet)));
  }

  function addTweet() {
    setTweets((rows) => [...rows, ""]);
  }

  function removeTweet(index: number) {
    setTweets((rows) => (rows.length > 1 ? rows.filter((_, i) => i !== index) : rows));
  }

  function moveTweet(index: number, delta: -1 | 1) {
    setTweets((rows) => {
      const target = index + delta;
      if (target < 0 || target >= rows.length) {
        return rows;
      }
      const next = [...rows];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  const hasOverlongTweet = tweets.some((tweet) => tweet.length > TWEET_MAX_CHARS);
  const hasEmptyTweet = tweets.some((tweet) => tweet.trim().length === 0);

  async function saveDraft() {
    if (!token || !selectedDraft) return;
    setSaving(true);
    try {
      const updated =
        selectedDraft.platform === "x"
          ? await updateAmplifyDraft(token, selectedDraft.id, { thread_json: tweets })
          : await updateAmplifyDraft(token, selectedDraft.id, { content: linkedinContent });
      applyUpdatedDraft(updated);
      success("Amplified draft saved");
    } catch (err: unknown) {
      error("Could not save draft", getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function publishToX() {
    if (!token || !selectedDraft) return;
    setPublishing(true);
    try {
      const result = await publishAmplifyDraft(token, selectedDraft.id);
      applyUpdatedDraft({ ...selectedDraft, thread_json: tweets, status: "published" });
      const firstUrl = result.tweets[0]?.url;
      success(
        `Thread published (${result.tweet_ids.length} tweet${result.tweet_ids.length === 1 ? "" : "s"})`,
        firstUrl
      );
    } catch (err: unknown) {
      const hint =
        isApiError(err) && err.status === 400
          ? ' If X is not connected yet, add your X access token in Settings → API Keys with provider "x".'
          : "";
      error("Could not publish to X", `${getErrorMessage(err)}${hint}`);
    } finally {
      setPublishing(false);
    }
  }

  async function copyLinkedinPost() {
    try {
      await copyText(linkedinContent);
      success("Formatted post copied", "Paste it into the LinkedIn composer.");
    } catch {
      error("Failed to copy", "Clipboard access was denied.");
    }
  }

  const linkedinLength = linkedinContent.length;
  const linkedinIdeal = linkedinLength >= LINKEDIN_MIN_IDEAL && linkedinLength <= LINKEDIN_MAX_IDEAL;

  return (
    <div className="space-y-6">
      <PageHeader title="Content Studio" description="Generated content briefs, posts, and amplified drafts." />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="articles">Article Briefs</TabsTrigger>
          <TabsTrigger value="x">X Posts</TabsTrigger>
          <TabsTrigger value="linkedin">LinkedIn Posts</TabsTrigger>
          <TabsTrigger value="ugc">UGC Briefs</TabsTrigger>
          <TabsTrigger value="amplified">
            Amplified
            {amplifyDrafts.length > 0 && (
              <Badge variant="secondary" className="ml-1.5">{amplifyDrafts.length}</Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="articles" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {articleBriefs.map((item, i) => (
            <Card key={i}>
              <CardHeader>
                <CardTitle className="text-base">{item.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Badge variant="secondary">{item.keyword}</Badge>
                <pre className="text-xs bg-muted rounded p-3 whitespace-pre-wrap">{item.outline}</pre>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(item.outline)}>
                    <Copy className="h-3.5 w-3.5 mr-1" />
                    Copy
                  </Button>
                  <Button variant="outline" size="sm">
                    <Download className="h-3.5 w-3.5 mr-1" />
                    Export MD
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="x" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {xPosts.map((item, i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-3">
                <Badge variant="secondary" className="text-[11px]">{item.type}</Badge>
                <p className="text-sm leading-relaxed">{item.text}</p>
                <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(item.text)}>
                  <Copy className="h-3.5 w-3.5 mr-1" />
                  Copy
                </Button>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="linkedin" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {linkedInPosts.map((item, i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-3">
                <Badge variant="secondary" className="text-[11px]">{item.type}</Badge>
                <p className="text-sm leading-relaxed">{item.text}</p>
                <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(item.text)}>
                  <Copy className="h-3.5 w-3.5 mr-1" />
                  Copy
                </Button>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="ugc" className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ugcBriefs.map((item, i) => (
            <Card key={i}>
              <CardContent className="p-4 space-y-3">
                <p className="text-sm font-medium">{item.hook}</p>
                <div className="text-xs text-muted-foreground">
                  {item.scenes} scenes · {item.duration}
                </div>
                <Button variant="outline" size="sm">
                  <Download className="h-3.5 w-3.5 mr-1" />
                  Export Brief
                </Button>
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* Amplified drafts: X threads / LinkedIn posts generated from reply drafts */}
        <TabsContent value="amplified">
          {amplifyDrafts.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center p-10 text-center">
                <Megaphone className="h-8 w-8 text-muted-foreground/50" />
                <h3 className="mt-3 text-sm font-semibold">No amplified drafts in this session</h3>
                <p className="mt-1 max-w-md text-xs text-muted-foreground">
                  Open Content → Reply Queue and use &quot;Amplify to X thread&quot; or &quot;Amplify to
                  LinkedIn&quot; on a reply draft. The generated draft opens here for editing and publishing.
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-[18rem_1fr]">
              {/* Draft list */}
              <div className="space-y-2">
                {amplifyDrafts.map((draft) => (
                  <button
                    key={draft.id}
                    type="button"
                    onClick={() => setSelectedDraftId(draft.id)}
                    className={cn(
                      "w-full rounded-lg border p-3 text-left transition-colors hover:bg-accent/50",
                      selectedDraft?.id === draft.id && "border-primary bg-accent/40"
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-[11px] uppercase">
                        {draft.platform === "x" ? "X thread" : draft.platform}
                      </Badge>
                      <Badge variant="outline" className="text-[11px] capitalize">{draft.status}</Badge>
                    </div>
                    <p className="mt-2 line-clamp-2 text-xs text-muted-foreground">
                      {draft.platform === "x"
                        ? draft.thread_json[0] || "Empty thread"
                        : (draft.content ?? "").slice(0, 140) || "Empty post"}
                    </p>
                    <p className="mt-1 text-[11px] text-muted-foreground/70">
                      {new Date(draft.created_at).toLocaleString()}
                    </p>
                  </button>
                ))}
              </div>

              {/* Editor */}
              {!selectedDraft ? (
                <Card>
                  <CardContent className="flex items-center justify-center p-10 text-sm text-muted-foreground">
                    Select an amplified draft to edit it.
                  </CardContent>
                </Card>
              ) : selectedDraft.platform === "x" ? (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">X Thread Editor</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {tweets.map((tweet, index) => (
                      <div key={index} className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <Label className="text-xs text-muted-foreground">Tweet {index + 1}</Label>
                          <div className="flex items-center gap-1">
                            <Button
                              variant="ghost"
                              size="icon-xs"
                              onClick={() => moveTweet(index, -1)}
                              disabled={index === 0}
                              aria-label={`Move tweet ${index + 1} up`}
                            >
                              <ArrowUp className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-xs"
                              onClick={() => moveTweet(index, 1)}
                              disabled={index === tweets.length - 1}
                              aria-label={`Move tweet ${index + 1} down`}
                            >
                              <ArrowDown className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon-xs"
                              onClick={() => removeTweet(index)}
                              disabled={tweets.length === 1}
                              aria-label={`Remove tweet ${index + 1}`}
                            >
                              <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                            </Button>
                          </div>
                        </div>
                        <Textarea
                          rows={3}
                          value={tweet}
                          onChange={(event) => updateTweet(index, event.target.value)}
                          className={cn(
                            "text-sm leading-relaxed",
                            tweet.length > TWEET_MAX_CHARS && "border-destructive focus-visible:ring-destructive"
                          )}
                        />
                        <p
                          className={cn(
                            "text-right text-xs",
                            tweet.length > TWEET_MAX_CHARS
                              ? "font-semibold text-destructive"
                              : "text-muted-foreground"
                          )}
                        >
                          {tweet.length}/{TWEET_MAX_CHARS}
                        </p>
                      </div>
                    ))}

                    <Button variant="outline" size="sm" onClick={addTweet}>
                      <Plus className="h-3.5 w-3.5" /> Add tweet
                    </Button>

                    <div className="flex flex-wrap gap-2 border-t pt-4">
                      <Button onClick={() => void saveDraft()} disabled={saving || hasEmptyTweet}>
                        {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                        Save
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => void publishToX()}
                        disabled={publishing || hasOverlongTweet || hasEmptyTweet || selectedDraft.status === "published"}
                      >
                        {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                        {selectedDraft.status === "published" ? "Published" : "Publish to X"}
                      </Button>
                      {hasOverlongTweet && (
                        <p className="self-center text-xs text-destructive">
                          Shorten tweets over {TWEET_MAX_CHARS} characters before publishing.
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">LinkedIn Post Editor</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Textarea
                      rows={14}
                      value={linkedinContent}
                      onChange={(event) => setLinkedinContent(event.target.value)}
                      className="text-sm leading-relaxed"
                    />
                    <p className="text-xs">
                      <span className={cn(linkedinIdeal ? "font-medium text-success" : "text-muted-foreground")}>
                        {linkedinLength.toLocaleString()} characters
                      </span>{" "}
                      <span className="text-muted-foreground">
                        — LinkedIn posts perform best between 1,300 and 3,000 characters.
                      </span>
                    </p>
                    <div className="flex flex-wrap gap-2 border-t pt-4">
                      <Button onClick={() => void saveDraft()} disabled={saving || linkedinContent.trim().length === 0}>
                        {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                        Save
                      </Button>
                      <Button variant="outline" onClick={() => void copyLinkedinPost()}>
                        <Copy className="h-3.5 w-3.5" /> Copy formatted post
                      </Button>
                      <p className="self-center text-xs text-muted-foreground">
                        LinkedIn publishing is manual — paste into the composer.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
