"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type SecretRecord, type WebhookEndpoint } from "../../../lib/api";

export default function SettingsPage() {
  const { token } = useAuth();
  const [webhooks, setWebhooks] = useState<WebhookEndpoint[]>([]);
  const [secrets, setSecrets] = useState<SecretRecord[]>([]);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [secret, setSecret] = useState({ provider: "openai", label: "primary", value: "" });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    Promise.all([
      apiRequest<WebhookEndpoint[]>("/v1/webhooks", {}, token),
      apiRequest<SecretRecord[]>("/v1/secrets", {}, token)
    ])
      .then(([webhookRows, secretRows]) => {
        if (!ignore) {
          setWebhooks(webhookRows);
          setSecrets(secretRows);
        }
      })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [token]);

  async function createWebhook(event: FormEvent) {
    event.preventDefault();
    if (!token || !webhookUrl) {
      return;
    }
    try {
      const created = await apiRequest<WebhookEndpoint>("/v1/webhooks", {
        method: "POST",
        body: JSON.stringify({ target_url: webhookUrl, event_types: ["opportunity.found"], is_active: true })
      }, token);
      setWebhooks((rows) => [created, ...rows]);
      setWebhookUrl("");
      setMessage("Connection added.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not add the connection.");
    }
  }

  async function createSecret(event: FormEvent) {
    event.preventDefault();
    if (!token) {
      return;
    }
    try {
      const created = await apiRequest<SecretRecord>("/v1/secrets", {
        method: "POST",
        body: JSON.stringify(secret)
      }, token);
      setSecrets((rows) => [created, ...rows.filter((row) => row.id !== created.id)]);
      setSecret({ provider: "openai", label: "primary", value: "" });
      setMessage("Saved key added.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save the key.");
    }
  }

  return (
    <div className="split-grid">
      <section className="card">
        <div className="eyebrow">Connections</div>
        <h2>Optional: send updates to your own tools</h2>
        <p>You can ignore this while testing the product.</p>
        <form className="inline-form" onSubmit={createWebhook}>
          <input type="url" required value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} placeholder="https://your-app.com/webhook" />
          <button className="secondary-button" type="submit">Add connection</button>
        </form>
        <div className="item-list">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="list-row">
              <strong>{webhook.target_url}</strong>
              <p>Updates sent: {webhook.event_types.join(", ")}</p>
            </div>
          ))}
          {!webhooks.length ? <div className="empty-state">No connections added yet.</div> : null}
        </div>
      </section>

      <section className="card">
        <div className="eyebrow">Saved keys</div>
        <h2>Optional: store API keys safely</h2>
        {message ? <div className="notice">{message}</div> : null}
        <form className="item-list" onSubmit={createSecret}>
          <label className="field">
            <span>Tool name</span>
            <input value={secret.provider} onChange={(event) => setSecret({ ...secret, provider: event.target.value })} />
          </label>
          <label className="field">
            <span>Name</span>
            <input value={secret.label} onChange={(event) => setSecret({ ...secret, label: event.target.value })} />
          </label>
          <label className="field">
            <span>Secret value</span>
            <input type="password" autoComplete="off" required value={secret.value} onChange={(event) => setSecret({ ...secret, value: event.target.value })} />
          </label>
          <button className="secondary-button" type="submit">Save key</button>
        </form>
        <div className="item-list">
          {secrets.map((record) => (
            <div key={record.id} className="list-row">
              <strong>{record.provider}</strong>
              <p>{record.label}</p>
            </div>
          ))}
          {!secrets.length ? <div className="empty-state">No saved keys yet.</div> : null}
        </div>
      </section>
    </div>
  );
}
