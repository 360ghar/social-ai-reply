"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type PromptTemplate } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

export default function PromptsPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) return;
    let ignore = false;
    fetchDashboard(token)
      .then((data) => { if (!ignore) setDashboard(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [token]);

  useEffect(() => {
    if (!token || !project) return;
    let ignore = false;
    apiRequest<PromptTemplate[]>(`/v1/prompts?project_id=${project.id}`, {}, token)
      .then((data) => { if (!ignore) setPrompts(data); })
      .catch((err) => { if (!ignore) setMessage(err.message); });
    return () => { ignore = true; };
  }, [project, token]);

  async function updatePrompt(event: FormEvent<HTMLFormElement>, prompt: PromptTemplate) {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    try {
      const updated = await apiRequest<PromptTemplate>(`/v1/prompts/${prompt.id}`, {
        method: "PUT",
        body: JSON.stringify(prompt)
      }, token);
      setPrompts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      setMessage("Writing rule saved.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save writing rule.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="card">
      <div className="eyebrow">Writing style</div>
      <h2>Optional: change how AI drafts are written</h2>
      <p>You can ignore this page at first. The default writing rules already work.</p>
      {message ? <div className="notice">{message}</div> : null}
      <div className="item-list">
        {prompts.map((prompt) => (
          <form key={prompt.id} className="list-row" onSubmit={(event) => updatePrompt(event, prompt)}>
            <strong>{prompt.name}</strong>
            <label className="field">
              <span>Core rule</span>
              <textarea
                value={prompt.system_prompt}
                onChange={(event) =>
                  setPrompts((rows) =>
                    rows.map((row) => (row.id === prompt.id ? { ...row, system_prompt: event.target.value } : row))
                  )
                }
              />
            </label>
            <label className="field">
              <span>Extra instructions</span>
              <textarea
                value={prompt.instructions}
                onChange={(event) =>
                  setPrompts((rows) =>
                    rows.map((row) => (row.id === prompt.id ? { ...row, instructions: event.target.value } : row))
                  )
                }
              />
            </label>
            <button className="secondary-button" type="submit" disabled={saving}>{saving ? "Saving..." : "Save writing rule"}</button>
          </form>
        ))}
        {!prompts.length ? <div className="empty-state">Writing rules appear automatically after you create a business.</div> : null}
      </div>
    </section>
  );
}
