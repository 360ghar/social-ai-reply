"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type Persona } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

const emptyPersona = {
  name: "",
  role: "",
  summary: "",
  pain_points: [] as string[],
  goals: [] as string[],
  triggers: [] as string[],
  preferred_subreddits: [] as string[],
  source: "manual",
  is_active: true
};

export default function PersonaPage() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [draft, setDraft] = useState(emptyPersona);
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
    apiRequest<Persona[]>(`/v1/personas?project_id=${project.id}`, {}, token).then(setPersonas).catch((err) => setMessage(err.message));
  }, [project, token]);

  async function createPersona(event: FormEvent) {
    event.preventDefault();
    if (!token || !project) {
      return;
    }
    try {
      const created = await apiRequest<Persona>(`/v1/personas?project_id=${project.id}`, {
        method: "POST",
        body: JSON.stringify(draft)
      }, token);
      setPersonas((rows) => [created, ...rows]);
      setDraft(emptyPersona);
      setMessage("Customer type saved.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save the customer type.");
    }
  }

  async function generateSeedPersonas() {
    if (!token || !project) {
      return;
    }
    try {
      const created = await apiRequest<Persona[]>(`/v1/personas/generate?project_id=${project.id}&count=4`, {
        method: "POST"
      }, token);
      setPersonas((rows) => [...created, ...rows.filter((row) => !created.some((item) => item.id === row.id))]);
      setMessage("Example customer types created.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create example customer types.");
    }
  }

  return (
    <div className="split-grid">
      <form className="card" onSubmit={createPersona}>
        <div className="eyebrow">Customers</div>
        <h2>Who do you want to help on Reddit?</h2>
        <p>Write 2 or 3 customer types in simple language. Example: "Small business owner looking for a better CRM".</p>
        <label className="field">
          <span>Customer type</span>
          <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        </label>
        <label className="field">
          <span>Job title or role</span>
          <input value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value })} />
        </label>
        <label className="field">
          <span>What do they want?</span>
          <textarea value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} />
        </label>
        <div className="action-row">
          <button className="secondary-button" type="submit">Save customer type</button>
          <button className="primary-button" type="button" onClick={generateSeedPersonas}>Create examples</button>
        </div>
        {message ? <div className="notice">{message}</div> : null}
      </form>

      <section className="card">
        <div className="eyebrow">Saved customers</div>
        <h2>People you want to reach</h2>
        <div className="item-list">
          {personas.map((persona) => (
            <div key={persona.id} className="list-row">
              <strong>{persona.name}</strong>
              <p>{persona.summary}</p>
              <div className="badge-row">
                <span className="badge">{persona.role ?? "Role not set"}</span>
                <span className="badge">{persona.source === "generated" ? "Created by AI" : "Added by you"}</span>
              </div>
            </div>
          ))}
          {!personas.length ? <div className="empty-state">No customer types yet. Add one yourself or create examples.</div> : null}
        </div>
      </section>
    </div>
  );
}
