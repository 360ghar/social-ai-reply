"use client";

import { FormEvent, useEffect, useState } from "react";
import { useToast } from "../../../components/toast";
import { ConfirmModal } from "../../../components/modal";
import { Button, EmptyState, Tabs } from "../../../components/ui";
import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type SecretRecord, type WebhookEndpoint } from "../../../lib/api";

const PROVIDERS = ["openai", "perplexity", "gemini", "claude", "reddit", "custom"];
const EVENT_TYPES = ["opportunity.found", "scan.complete", "visibility.alert", "draft.ready"];

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
      const [webhookRows, secretRows] = await Promise.all([
        apiRequest<WebhookEndpoint[]>("/v1/webhooks", {}, token),
        apiRequest<SecretRecord[]>("/v1/secrets", {}, token),
      ]);
      setWebhooks(webhookRows);
      setSecrets(secretRows);
    } catch (err) {
      toast.error("Failed to load settings", err instanceof Error ? err.message : undefined);
    }
  }

  async function saveGeneralSettings() {
    setLoading(true);
    try {
      // Mock API call - replace with actual endpoint
      await new Promise((resolve) => setTimeout(resolve, 500));
      toast.success("Settings saved", "Your workspace settings have been updated");
    } catch (err) {
      toast.error("Failed to save settings", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
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
    setLoading(true);
    try {
      // Mock export
      await new Promise((resolve) => setTimeout(resolve, 800));
      toast.success("Export started", "Check your email for the data export file");
    } catch (err) {
      toast.error("Failed to export", err instanceof Error ? err.message : undefined);
    } finally {
      setLoading(false);
    }
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
    <div className="card">
      <div className="eyebrow">Settings</div>
      <h1>Workspace Settings</h1>

      <Tabs
        tabs={[
          { key: "general", label: "General" },
          { key: "api-keys", label: "API Keys", count: secrets.length },
          { key: "integrations", label: "Integrations", count: webhooks.length },
          { key: "danger", label: "Danger Zone" },
        ]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* GENERAL TAB */}
      {activeTab === "general" && (
        <div style={{ marginTop: 24 }}>
          <section style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 16 }}>Workspace</h3>
            <label className="field">
              <span>Workspace name</span>
              <input
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                placeholder="My Workspace"
              />
            </label>
          </section>

          <section style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 16 }}>User Profile</h3>
            <label className="field">
              <span>Full name</span>
              <input
                value={userProfile.name}
                onChange={(e) => setUserProfile({ ...userProfile, name: e.target.value })}
                placeholder="Your name"
              />
            </label>
            <label className="field" style={{ marginTop: 12 }}>
              <span>Email</span>
              <input
                type="email"
                value={userProfile.email}
                onChange={(e) => setUserProfile({ ...userProfile, email: e.target.value })}
                placeholder="your@email.com"
                disabled
              />
            </label>
          </section>

          <section style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 16 }}>Notifications</h3>
            <label className="field" style={{ marginBottom: 12 }}>
              <input
                type="checkbox"
                checked={notifications.emailNotifications}
                onChange={(e) =>
                  setNotifications({ ...notifications, emailNotifications: e.target.checked })
                }
              />
              <span>Email notifications</span>
            </label>
            <label className="field" style={{ marginBottom: 12 }}>
              <input
                type="checkbox"
                checked={notifications.digestEmail}
                onChange={(e) =>
                  setNotifications({ ...notifications, digestEmail: e.target.checked })
                }
              />
              <span>Weekly digest email</span>
            </label>
            <label className="field">
              <input
                type="checkbox"
                checked={notifications.slackNotifications}
                onChange={(e) =>
                  setNotifications({ ...notifications, slackNotifications: e.target.checked })
                }
              />
              <span>Slack notifications</span>
            </label>
          </section>

          <div className="action-row" style={{ justifyContent: "flex-start" }}>
            <Button variant="primary" onClick={saveGeneralSettings} loading={loading}>
              Save changes
            </Button>
          </div>
        </div>
      )}

      {/* API KEYS TAB */}
      {activeTab === "api-keys" && (
        <div style={{ marginTop: 24 }}>
          <section style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 16 }}>Add API Key</h3>
            <form onSubmit={createSecret}>
              <label className="field">
                <span>Provider</span>
                <select
                  value={newSecret.provider}
                  onChange={(e) => setNewSecret({ ...newSecret, provider: e.target.value })}
                >
                  {PROVIDERS.map((p) => (
                    <option key={p} value={p}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field" style={{ marginTop: 12 }}>
                <span>Label</span>
                <input
                  value={newSecret.label}
                  onChange={(e) => setNewSecret({ ...newSecret, label: e.target.value })}
                  placeholder="e.g., Production key"
                />
              </label>
              <label className="field" style={{ marginTop: 12 }}>
                <span>Secret value</span>
                <input
                  type="password"
                  value={newSecret.value}
                  onChange={(e) => setNewSecret({ ...newSecret, value: e.target.value })}
                  placeholder="Paste your API key here"
                />
              </label>
              <div className="action-row" style={{ marginTop: 16, justifyContent: "flex-start" }}>
                <Button variant="primary" type="submit" loading={loading}>
                  Save API key
                </Button>
              </div>
            </form>
          </section>

          <section>
            <h3 style={{ marginBottom: 16 }}>Saved Keys</h3>
            {secrets.length === 0 ? (
              <EmptyState
                icon="🔑"
                title="No API keys saved"
                description="Add your first API key to get started"
              />
            ) : (
              <div className="item-list">
                {secrets.map((secret) => (
                  <div key={secret.id} className="list-row">
                    <div>
                      <strong>{secret.provider}</strong>
                      <p style={{ fontSize: "0.9em", marginTop: 4 }}>{secret.label}</p>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <code style={{ fontSize: "0.85em", color: "var(--muted)" }}>
                        {maskSecret(secret.id.toString())}
                      </code>
                      <button
                        className="ghost-button"
                        style={{ marginLeft: 12 }}
                        onClick={() => setDeleteSecretId(secret.id)}
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* INTEGRATIONS TAB */}
      {activeTab === "integrations" && (
        <div style={{ marginTop: 24 }}>
          <section style={{ marginBottom: 32 }}>
            <h3 style={{ marginBottom: 16 }}>Add Webhook</h3>
            <form onSubmit={createWebhook}>
              <label className="field">
                <span>Webhook URL</span>
                <input
                  value={newWebhook.url}
                  onChange={(e) => setNewWebhook({ ...newWebhook, url: e.target.value })}
                  placeholder="https://your-app.com/webhook"
                  type="url"
                />
              </label>
              <label className="field" style={{ marginTop: 12 }}>
                <span>Events to receive</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
                  {EVENT_TYPES.map((event) => (
                    <label key={event} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        type="checkbox"
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
              </label>
              <div className="action-row" style={{ marginTop: 16, justifyContent: "flex-start" }}>
                <Button variant="primary" type="submit" loading={loading}>
                  Add webhook
                </Button>
              </div>
            </form>
          </section>

          <section>
            <h3 style={{ marginBottom: 16 }}>Active Webhooks</h3>
            {webhooks.length === 0 ? (
              <EmptyState
                icon="🪝"
                title="No webhooks configured"
                description="Add a webhook to receive event notifications"
              />
            ) : (
              <div className="item-list">
                {webhooks.map((webhook) => (
                  <div key={webhook.id} className="list-row">
                    <div style={{ flex: 1 }}>
                      <strong>{webhook.target_url}</strong>
                      <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                        {webhook.event_types.map((type) => (
                          <span key={type} className="badge">
                            {type}
                          </span>
                        ))}
                      </div>
                      {webhook.last_tested_at && (
                        <p style={{ fontSize: "0.85em", marginTop: 8, color: "var(--muted)" }}>
                          Last tested: {new Date(webhook.last_tested_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <Button
                        variant="ghost"
                        onClick={() => toggleWebhook(webhook.id, webhook.is_active)}
                        loading={loading}
                      >
                        {webhook.is_active ? "Disable" : "Enable"}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => testWebhook(webhook.id)}
                        loading={testingWebhookId === webhook.id}
                      >
                        Test
                      </Button>
                      <button
                        className="ghost-button"
                        onClick={() => setDeleteWebhookId(webhook.id)}
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {/* DANGER ZONE TAB */}
      {activeTab === "danger" && (
        <div style={{ marginTop: 24 }}>
          <section style={{ padding: 16, backgroundColor: "#ffe5e5", borderRadius: 8, marginBottom: 32 }}>
            <h3 style={{ color: "#c41e3a", marginBottom: 16 }}>Export data</h3>
            <p style={{ marginBottom: 16 }}>
              Download a copy of all your data in JSON format. This includes your workspace configuration,
              settings, and history.
            </p>
            <Button variant="secondary" onClick={exportData} loading={loading}>
              Download data export
            </Button>
          </section>

          <section style={{ padding: 16, backgroundColor: "#ffe5e5", borderRadius: 8 }}>
            <h3 style={{ color: "#c41e3a", marginBottom: 16 }}>Delete workspace</h3>
            <p style={{ marginBottom: 16 }}>
              Permanently delete this workspace and all associated data. This action cannot be undone.
            </p>
            <label className="field">
              <span>Type "DELETE WORKSPACE" to confirm</span>
              <input
                value={deleteWorkspaceConfirm}
                onChange={(e) => setDeleteWorkspaceConfirm(e.target.value)}
                placeholder="DELETE WORKSPACE"
              />
            </label>
            <div className="action-row" style={{ marginTop: 16, justifyContent: "flex-start" }}>
              <Button
                variant="danger"
                onClick={() => deleteWorkspace()}
                disabled={deleteWorkspaceConfirm !== "DELETE WORKSPACE" || loading}
                loading={loading}
              >
                Delete workspace permanently
              </Button>
            </div>
          </section>
        </div>
      )}

      {/* Confirm modals */}
      <ConfirmModal
        open={deleteSecretId !== null}
        onClose={() => setDeleteSecretId(null)}
        onConfirm={() => deleteSecret(deleteSecretId!)}
        title="Delete API key"
        message="Are you sure you want to delete this API key? This action cannot be undone."
        confirmText="Delete"
        danger
        loading={loading}
      />

      <ConfirmModal
        open={deleteWebhookId !== null}
        onClose={() => setDeleteWebhookId(null)}
        onConfirm={() => deleteWebhook(deleteWebhookId!)}
        title="Delete webhook"
        message="Are you sure you want to delete this webhook? Your integrations will no longer receive events."
        confirmText="Delete"
        danger
        loading={loading}
      />
    </div>
  );
}
