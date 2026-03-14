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

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token).then(setDashboard).catch((err) => setMessage(err.message));
  }, [token]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    apiRequest<PromptTemplate[]>(`/v1/prompts?project_id=${project.id}`, {}, token).then(setPrompts).catch((err) => setMessage(err.message));
  }, [project, token]);

  async function updatePrompt(event: FormEvent<HTMLFormElement>, prompt: PromptTemplate) {
    event.preventDefault();
    if (!token) {
      return;
    }
    const updated = await apiRequest<PromptTemplate>(`/v1/prompts/${prompt.id}`, {
      method: "PUT",
      body: JSON.stringify(prompt)
    }, token);
    setPrompts((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
    setMessage("Writing rule saved.");
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
            <button className="secondary-button" type="submit">Save writing rule</button>
          </form>
        ))}
        {!prompts.length ? <div className="empty-state">Writing rules appear automatically after you create a business.</div> : null}
      </div>
    </section>
  );
}
