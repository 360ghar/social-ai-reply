"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "@/stores/toast";
import { useAuth } from "@/components/auth/auth-provider";
import { apiRequest, type SecretRecord, type WebhookEndpoint } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, Trash2 } from "lucide-react";

const PROVIDERS = ["openai", "perplexity", "gemini", "claude", "reddit", "custom"];
const EVENT_TYPES = ["opportunity.found", "scan.complete", "visibility.alert", "draft.ready"];

interface RedditAccount {
  id: number;
  username: string;
  karma?: number;
  connected_at?: string;
}

export default function SettingsPage() {
  const { token, user } = useAuth();
  const toast = useToast();
  const [activeTab, setActiveTab] = useState("general");
  const [loading, setLoading] = useState(false);

  // General tab state
  const [workspaceName, setWorkspaceName] = useState("My Workspace");
  const [userProfile, setUserProfile] = useState({ name: user?.full_name || "", email: user?.email || "" });
  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    digestEmail: false,
    slackNotifications: false,
  });

  // API Keys tab state
  const [secrets, setSecrets] = useState<SecretRecord[]>([]);
  const [newSecret, setNewSecret] = useState({ provider: "openai", label: "", value: "" });
  const [deleteSecretId, setDeleteSecretId] = useState<number | null>(null);

  // Integrations tab state
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [newWebhook, setNewWebhook] = useState({
    url: "",
    eventTypes: [] as string[],
  });
  const [deleteWebhookId, setDeleteWebhookId] = useState<number | null>(null);
  const [testingWebhookId, setTestingWebhookId] = useState<number | null>(null);

  // Danger zone state
  const [deleteWorkspaceConfirm, setDeleteWorkspaceConfirm] = useState("");

  // Reddit state
  const [redditAccounts, setRedditAccounts] = useState<RedditAccount[]>([]);
  const [connectingReddit, setConnectingReddit] = useState(false);
  const [disconnectingReddit, setDisconnectingReddit] = useState<number | null>(null);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token]);

  useEffect(() => {
    setUserProfile({ name: user?.full_name || "", email: user?.email || "" });
  }, [user]);

  async function loadData() {
    if (!token) return;
    try {
      const [webhookRows, secretRows, redditRows] = await Promise.all([
        apiRequest<WebhookEndpoint[]>("/v1/webhooks", {}, token),
        apiRequest<SecretRecord[]>("/v1/secrets", {}, token),
        apiRequest<RedditAccount[]>("/v1/reddit/accounts", {}, token).catch(() => []),
      ]);
      setWebhooks(webhookRows);
      setSecrets(secretRows);
      setRedditAccounts(redditRows);
    } catch (err) {
      toast.error("Failed to load settings", err instanceof Error ? err.message : undefined);
    }
  }

  async function connectReddit() {
    if (!token) return;
    setConnectingReddit(true);
    try {
      const result = await apiRequest<{ auth_url: string }>("/v1/reddit/connect", { method: "POST" }, token);
      if (result.auth_url) {
        window.open(result.auth_url, "_blank", "width=600,height=700");
        setTimeout(() => void loadData(), 3000);
      }
    } catch (err) {
      toast.error("Failed to connect Reddit", err instanceof Error ? err.message : undefined);
    }
    setConnectingReddit(false);
  }

  async function disconnectReddit(accountId: number) {
    if (!token) return;
    setDisconnectingReddit(accountId);
    try {
      await apiRequest(`/v1/reddit/accounts/${accountId}`, { method: "DELETE" }, token);
      setRedditAccounts((rows) => rows.filter((r) => r.id !== accountId));
      toast.success("Reddit account disconnected");
    } catch (err) {
      toast.error("Failed to disconnect", err instanceof Error ? err.message : undefined);
    }
    setDisconnectingReddit(null);
  }

  async function saveGeneralSettings() {
    // Not yet implemented — show a "coming soon" notice instead of a fake success.
    toast.info("Coming soon", "Workspace settings persistence is not yet available.");
  }

  async function createSecret(e: FormEvent) {
    e.preventDefault();
    if (!token || !newSecret.provider || !newSecret.label || !newSecret.value) {
      toast.warning("Invalid input", "Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const created = await apiRequest<SecretRecord>("/v1/secrets", {
        method: "POST",
        body: JSON.stringify(newSecret),
      }, token);
      setSecrets((rows) => [created, ...rows]);
      setNewSecret({ provider: "openai", label: "", value: "" });
      toast.success("API key saved", "Your secret has been securely stored");
    } catch (err) {
      toast.error("Failed to save key", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  async function deleteSecret(id: number) {
    if (!token) return;
    setLoading(true);
    try {
      await apiRequest("/v1/secrets/" + id, { method: "DELETE" }, token);
      setSecrets((rows) => rows.filter((r) => r.id !== id));
      setDeleteSecretId(null);
      toast.success("API key deleted", "The secret has been removed");
    } catch (err) {
      toast.error("Failed to delete key", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  async function createWebhook(e: FormEvent) {
    e.preventDefault();
    if (!token || !newWebhook.url || newWebhook.eventTypes.length === 0) {
      toast.warning("Invalid input", "Please provide a URL and select at least one event");
      return;
    }
    setLoading(true);
    try {
      const created = await apiRequest<WebhookEndpoint>("/v1/webhooks", {
        method: "POST",
        body: JSON.stringify({
          target_url: newWebhook.url,
          event_types: newWebhook.eventTypes,
          is_active: true,
        }),
      }, token);
      setWebhooks((rows) => [created, ...rows]);
      setNewWebhook({ url: "", eventTypes: [] });
      toast.success("Webhook added", "Your integration has been configured");
    } catch (err) {
      toast.error("Failed to create webhook", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  async function toggleWebhook(id: number, isActive: boolean) {
    if (!token) return;
    setLoading(true);
    try {
      const updated = await apiRequest<WebhookEndpoint>("/v1/webhooks/" + id, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !isActive }),
      }, token);
      setWebhooks((rows) => rows.map((r) => (r.id === id ? updated : r)));
      toast.success(
        !isActive ? "Webhook enabled" : "Webhook disabled",
        "Your integration status has been updated"
      );
    } catch (err) {
      toast.error("Failed to update webhook", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  async function testWebhook(id: number) {
    if (!token) return;
    setTestingWebhookId(id);
    try {
      await apiRequest(`/v1/webhooks/${id}/test`, { method: "POST" }, token);
      toast.success("Webhook test sent", "Check your endpoint for the test payload");
    } catch (err) {
      toast.error("Failed to test webhook", err instanceof Error ? err.message : undefined);
    } finally {
      setTestingWebhookId(null);
    }
  }

  async function deleteWebhook(id: number) {
    if (!token) return;
    setLoading(true);
    try {
      await apiRequest("/v1/webhooks/" + id, { method: "DELETE" }, token);
      setWebhooks((rows) => rows.filter((r) => r.id !== id));
      setDeleteWebhookId(null);
      toast.success("Webhook deleted", "Your integration has been removed");
    } catch (err) {
      toast.error("Failed to delete webhook", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  async function exportData() {
    // Not yet implemented — show a "coming soon" notice instead of a fake success.
    toast.info("Coming soon", "Data export is not yet available.");
  }

  async function deleteWorkspace() {
    if (!token || deleteWorkspaceConfirm !== "DELETE WORKSPACE") return;
    setLoading(true);
    try {
      await apiRequest("/v1/workspace", { method: "DELETE" }, token);
      toast.success("Workspace deleted", "Redirecting...");
      setTimeout(() => (window.location.href = "/"), 2000);
    } catch (err) {
      toast.error("Failed to delete workspace", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
  }

  const maskSecret = (secret: string) => {
    if (!secret || secret.length < 4) return "***";
    return secret.slice(0, 3) + "..." + secret.slice(-3);
  };

  return (
    <Card className="p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Settings
      </div>
      <h1 className="mb-6 text-lg font-semibold text-foreground">Workspace Settings</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="reddit">
            Reddit
            {redditAccounts.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">{redditAccounts.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="api-keys">
            API Keys
            {secrets.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">{secrets.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="integrations">
            Integrations
            {webhooks.length > 0 && (
              <Badge variant="secondary" className="ml-1.5 text-xs">{webhooks.length}</Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="danger">Danger Zone</TabsTrigger>
        </TabsList>

        {/* GENERAL TAB */}
        <TabsContent value="general">
          <div className="mt-6 grid gap-8">
            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Workspace</h3>
              <div className="grid gap-2">
                <Label htmlFor="workspace-name">Workspace name</Label>
                <Input
                  id="workspace-name"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="My Workspace"
                />
              </div>
            </section>

            <Separator />

            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">User Profile</h3>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="full-name">Full name</Label>
                  <Input
                    id="full-name"
                    value={userProfile.name}
                    onChange={(e) => setUserProfile({ ...userProfile, name: e.target.value })}
                    placeholder="Your name"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={userProfile.email}
                    onChange={(e) => setUserProfile({ ...userProfile, email: e.target.value })}
                    placeholder="your@email.com"
                    disabled
                  />
                </div>
              </div>
            </section>

            <Separator />

            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Notifications</h3>
              <div className="grid gap-3">
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-input"
                    checked={notifications.emailNotifications}
                    onChange={(e) =>
                      setNotifications({ ...notifications, emailNotifications: e.target.checked })
                    }
                  />
                  <span>Email notifications</span>
                </label>
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-input"
                    checked={notifications.digestEmail}
                    onChange={(e) =>
                      setNotifications({ ...notifications, digestEmail: e.target.checked })
                    }
                  />
                  <span>Weekly digest email</span>
                </label>
                <label className="flex items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    className="size-4 rounded border-input"
                    checked={notifications.slackNotifications}
                    onChange={(e) =>
                      setNotifications({ ...notifications, slackNotifications: e.target.checked })
                    }
                  />
                  <span>Slack notifications</span>
                </label>
              </div>
            </section>

            <div className="flex flex-wrap gap-2">
              <Button onClick={saveGeneralSettings} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                Save changes
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* REDDIT TAB */}
        <TabsContent value="reddit">
          <div className="mt-6">
            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Reddit Accounts</h3>
              {redditAccounts.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-center">
                  <span className="mb-4 text-4xl">🔗</span>
                  <h3 className="mb-1 text-sm font-semibold text-foreground">No Reddit accounts connected</h3>
                  <p className="mb-4 text-xs text-muted-foreground">
                    Connect a Reddit account to enable automated posting and engagement
                  </p>
                  <Button onClick={() => void connectReddit()} disabled={connectingReddit}>
                    {connectingReddit && <Loader2 className="h-4 w-4 animate-spin" />}
                    Connect Reddit Account
                  </Button>
                </div>
              ) : (
                <div className="grid gap-3">
                  {redditAccounts.map((account) => (
                    <div
                      key={account.id}
                      className="flex items-center justify-between rounded-lg border bg-card p-4"
                    >
                      <div>
                        <div className="mb-1 text-sm font-semibold text-foreground">@{account.username}</div>
                        {account.karma !== undefined && (
                          <p className="text-xs text-muted-foreground">Karma: {account.karma}</p>
                        )}
                        {account.connected_at && (
                          <p className="text-xs text-muted-foreground">
                            Connected: {new Date(account.connected_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => void disconnectReddit(account.id)}
                        disabled={disconnectingReddit === account.id}
                      >
                        {disconnectingReddit === account.id && <Loader2 className="h-4 w-4 animate-spin" />}
                        Disconnect
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    onClick={() => void connectReddit()}
                    disabled={connectingReddit}
                    className="mt-3"
                  >
                    {connectingReddit && <Loader2 className="h-4 w-4 animate-spin" />}
                    Connect Additional Account
                  </Button>
                </div>
              )}
            </section>
          </div>
        </TabsContent>

        {/* API KEYS TAB */}
        <TabsContent value="api-keys">
          <div className="mt-6 grid gap-8">
            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Add API Key</h3>
              <form onSubmit={createSecret} className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="secret-provider">Provider</Label>
                  <Select
                    value={newSecret.provider}
                    onValueChange={(value) => setNewSecret({ ...newSecret, provider: value ?? "openai" })}
                  >
                    <SelectTrigger id="secret-provider" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVIDERS.map((p) => (
                        <SelectItem key={p} value={p}>
                          {p.charAt(0).toUpperCase() + p.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="secret-label">Label</Label>
                  <Input
                    id="secret-label"
                    value={newSecret.label}
                    onChange={(e) => setNewSecret({ ...newSecret, label: e.target.value })}
                    placeholder="e.g., Production key"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="secret-value">Secret value</Label>
                  <Input
                    id="secret-value"
                    type="password"
                    value={newSecret.value}
                    onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
                    placeholder="Paste your API key here"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={loading}>
                    {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                    Save API key
                  </Button>
                </div>
              </form>
            </section>

            <Separator />

            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Saved Keys</h3>
              {secrets.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-center">
                  <span className="mb-4 text-4xl">🔑</span>
                  <h3 className="mb-1 text-sm font-semibold text-foreground">No API keys saved</h3>
                  <p className="text-xs text-muted-foreground">Add your first API key to get started</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {secrets.map((secret) => (
                    <div key={secret.id} className="flex items-center justify-between rounded-lg border bg-card p-4">
                      <div>
                        <strong className="text-sm font-medium text-foreground">{secret.provider}</strong>
                        <p className="mt-1 text-sm text-muted-foreground">{secret.label}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <code className="text-xs text-muted-foreground">
                          {maskSecret(secret.id.toString())}
                        </code>
                        <Button
                          variant="ghost"
                          size="icon-xs"
                          onClick={() => setDeleteSecretId(secret.id)}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </TabsContent>

        {/* INTEGRATIONS TAB */}
        <TabsContent value="integrations">
          <div className="mt-6 grid gap-8">
            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Add Webhook</h3>
              <form onSubmit={createWebhook} className="grid gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="webhook-url">Webhook URL</Label>
                  <Input
                    id="webhook-url"
                    type="url"
                    value={newWebhook.url}
                    onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })}
                    placeholder="https://your-app.com/webhook"
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Events to receive</Label>
                  <div className="mt-1 grid gap-2">
                    {EVENT_TYPES.map((event) => (
                      <label key={event} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          className="size-4 rounded border-input"
                          checked={newWebhook.eventTypes.includes(event)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setNewWebhook({
                                ...newWebhook,
                                eventTypes: [...newWebhook.eventTypes, event],
                              });
                            } else {
                              setNewWebhook({
                                ...newWebhook,
                                eventTypes: newWebhook.eventTypes.filter((t) => t !== event),
                              });
                            }
                          }}
                        />
                        <span>{event}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={loading}>
                    {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                    Add webhook
                  </Button>
                </div>
              </form>
            </section>

            <Separator />

            <section>
              <h3 className="mb-4 text-sm font-semibold text-foreground">Active Webhooks</h3>
              {webhooks.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-8 text-center">
                  <span className="mb-4 text-4xl">🪝</span>
                  <h3 className="mb-1 text-sm font-semibold text-foreground">No webhooks configured</h3>
                  <p className="text-xs text-muted-foreground">Add a webhook to receive event notifications</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {webhooks.map((webhook) => (
                    <div key={webhook.id} className="rounded-lg border bg-card p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1">
                          <strong className="text-sm font-medium text-foreground break-all">
                            {webhook.target_url}
                          </strong>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {webhook.event_types.map((type) => (
                              <Badge key={type} variant="secondary" className="text-xs">
                                {type}
                              </Badge>
                            ))}
                          </div>
                          {webhook.last_tested_at && (
                            <p className="mt-2 text-xs text-muted-foreground">
                              Last tested: {new Date(webhook.last_tested_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toggleWebhook(webhook.id, webhook.is_active)}
                            disabled={loading}
                          >
                            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                            {webhook.is_active ? "Disable" : "Enable"}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => testWebhook(webhook.id)}
                            disabled={testingWebhookId === webhook.id}
                          >
                            {testingWebhookId === webhook.id && <Loader2 className="h-4 w-4 animate-spin" />}
                            Test
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            onClick={() => setDeleteWebhookId(webhook.id)}
                          >
                            <Trash2 className="h-4 w-4 text-muted-foreground" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </TabsContent>

        {/* DANGER ZONE TAB */}
        <TabsContent value="danger">
          <div className="mt-6 grid gap-6">
            <section className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <h3 className="mb-4 text-sm font-semibold text-destructive">Export data</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Download a copy of all your data in JSON format. This includes your workspace configuration,
                settings, and history.
              </p>
              <Button variant="outline" onClick={exportData} disabled={loading}>
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                Download data export
              </Button>
            </section>

            <section className="rounded-lg border border-destructive/30 bg-destructive/5 p-4">
              <h3 className="mb-4 text-sm font-semibold text-destructive">Delete workspace</h3>
              <p className="mb-4 text-sm text-muted-foreground">
                Permanently delete this workspace and all associated data. This action cannot be undone.
              </p>
              <div className="grid gap-2">
                <Label htmlFor="delete-confirm">Type &quot;DELETE WORKSPACE&quot; to confirm</Label>
                <Input
                  id="delete-confirm"
                  value={deleteWorkspaceConfirm}
                  onChange={(e) => setDeleteWorkspaceConfirm(e.target.value)}
                  placeholder="DELETE WORKSPACE"
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  variant="destructive"
                  onClick={() => deleteWorkspace()}
                  disabled={deleteWorkspaceConfirm !== "DELETE WORKSPACE" || loading}
                >
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Delete workspace permanently
                </Button>
              </div>
            </section>
          </div>
        </TabsContent>
      </Tabs>

      {/* Confirm modals */}
      <AlertDialog open={deleteSecretId !== null} onOpenChange={(open) => { if (!open) setDeleteSecretId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete API key</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this API key? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => deleteSecret(deleteSecretId!)}
              disabled={loading}
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteWebhookId !== null} onOpenChange={(open) => { if (!open) setDeleteWebhookId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete webhook</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this webhook? Your integrations will no longer receive events.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => deleteWebhook(deleteWebhookId!)}
              disabled={loading}
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}
