"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { useToast } from "../../../components/toast";
import { Button, EmptyState, KpiCard, ConfirmModal, Drawer, SkeletonCard } from "../../../components/ui";
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
  const toast = useToast();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [draft, setDraft] = useState(emptyPersona);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEditingId, setIsEditingId] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token)
      .then(setDashboard)
      .catch((err) => {
        toast.error("Failed to load", err.message);
      });
  }, [token, toast]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setIsLoading(true);
    apiRequest<Persona[]>(`/v1/personas?project_id=${project.id}`, {}, token)
      .then((data) => {
        setPersonas(data);
        setIsLoading(false);
      })
      .catch((err) => {
        toast.error("Failed to load personas", err.message);
        setIsLoading(false);
      });
  }, [project, token, toast]);

  async function createPersona(event: FormEvent) {
    event.preventDefault();
    if (!token || !project) {
      return;
    }
    if (!draft.name.trim()) {
      toast.warning("Required field", "Please enter a customer type name.");
      return;
    }
    setIsCreating(true);
    try {
      const created = await apiRequest<Persona>(`/v1/personas?project_id=${project.id}`, {
        method: "POST",
        body: JSON.stringify(draft)
      }, token);
      setPersonas((rows) => [created, ...rows]);
      setDraft(emptyPersona);
      toast.success("Saved", "Customer type has been created.");
    } catch (err) {
      toast.error("Save failed", err instanceof Error ? err.message : "Could not save the customer type.");
    } finally {
      setIsCreating(false);
    }
  }

  async function updatePersona(event: FormEvent) {
    event.preventDefault();
    if (!token || !isEditingId) {
      return;
    }
    setIsUpdating(true);
    try {
      const updated = await apiRequest<Persona>(`/v1/personas/${isEditingId}`, {
        method: "PUT",
        body: JSON.stringify(draft)
      }, token);
      setPersonas((rows) => rows.map((p) => (p.id === isEditingId ? updated : p)));
      setDraft(emptyPersona);
      setIsEditingId(null);
      toast.success("Saved", "Customer type has been updated.");
    } catch (err) {
      toast.error("Update failed", err instanceof Error ? err.message : "Could not update the customer type.");
    } finally {
      setIsUpdating(false);
    }
  }

  async function togglePersona(personaId: string, currentActive: boolean) {
    if (!token) return;
    try {
      const persona = personas.find((p) => p.id === personaId);
      if (!persona) return;
      const updated = await apiRequest<Persona>(`/v1/personas/${personaId}`, {
        method: "PUT",
        body: JSON.stringify({ ...persona, is_active: !currentActive })
      }, token);
      setPersonas((rows) => rows.map((p) => (p.id === personaId ? updated : p)));
      toast.success(
        !currentActive ? "Activated" : "Deactivated",
        `Customer type "${persona.name}" is now ${!currentActive ? "active" : "inactive"}.`
      );
    } catch (err) {
      toast.error("Failed", err instanceof Error ? err.message : "Could not update status.");
    }
  }

  async function deletePersona() {
    if (!token || !deleteId) return;
    setIsDeleting(true);
    try {
      const persona = personas.find((p) => p.id === deleteId);
      await apiRequest(`/v1/personas/${deleteId}`, {
        method: "DELETE"
      }, token);
      setPersonas((rows) => rows.filter((p) => p.id !== deleteId));
      setDeleteId(null);
      toast.success("Deleted", `Customer type "${persona?.name}" has been removed.`);
    } catch (err) {
      toast.error("Delete failed", err instanceof Error ? err.message : "Could not delete the customer type.");
    } finally {
      setIsDeleting(false);
    }
  }

  async function generateSeedPersonas() {
    if (!token || !project) {
      return;
    }
    setIsGenerating(true);
    try {
      const created = await apiRequest<Persona[]>(`/v1/personas/generate?project_id=${project.id}&count=4`, {
        method: "POST"
      }, token);
      setPersonas((rows) => [...created, ...rows.filter((row) => !created.some((item) => item.id === row.id))]);
      toast.success("Created", "Example customer types have been generated.");
    } catch (err) {
      toast.error("Generation failed", err instanceof Error ? err.message : "Could not create example customer types.");
    } finally {
      setIsGenerating(false);
    }
  }

  const activeCount = personas.filter((p) => p.is_active).length;
  const aiCount = personas.filter((p) => p.source === "generated").length;

  if (isLoading) {
    return (
      <div>
        <div className="section-grid" style={{ marginBottom: "var(--space-lg)" }}>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div>
      <div className="section-grid" style={{ marginBottom: "var(--space-lg)" }}>
        <KpiCard label="Total Personas" value={personas.length} />
        <KpiCard label="Active" value={activeCount} />
        <KpiCard label="AI-Generated" value={aiCount} />
      </div>

      <div className="split-grid">
        <form className="card" onSubmit={isEditingId ? updatePersona : createPersona}>
          <div className="eyebrow">Customers</div>
          <h2>{isEditingId ? "Edit customer type" : "Who do you want to help on Reddit?"}</h2>
          <p>
            {isEditingId
              ? "Update this customer type."
              : "Write 2 or 3 customer types in simple language. Example: Small business owner looking for a better CRM."}
          </p>

          <label className="field">
            <span>Customer type</span>
            <input
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              placeholder="e.g., 'Small business owner'"
            />
          </label>

          <label className="field">
            <span>Job title or role</span>
            <input
              value={draft.role}
              onChange={(event) => setDraft({ ...draft, role: event.target.value })}
              placeholder="e.g., 'Marketing Manager'"
            />
          </label>

          <label className="field">
            <span>What do they want?</span>
            <textarea
              value={draft.summary}
              onChange={(event) => setDraft({ ...draft, summary: event.target.value })}
              placeholder="Describe what this customer type needs or wants..."
              rows={3}
            />
          </label>

          <div className="action-row" style={{ marginTop: "var(--space-lg)" }}>
            <Button variant="secondary" type="submit" loading={isCreating || isUpdating}>
              {isEditingId ? "Update" : "Save customer type"}
            </Button>
            {!isEditingId && (
              <Button
                variant="primary"
                type="button"
                onClick={generateSeedPersonas}
                loading={isGenerating}
              >
                Create examples
              </Button>
            )}
            {isEditingId && (
              <Button
                variant="ghost"
                type="button"
                onClick={() => {
                  setIsEditingId(null);
                  setDraft(emptyPersona);
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        </form>

        <section className="card">
          <div className="eyebrow">Saved customers</div>
          <h2>People you want to reach</h2>
          {personas.length === 0 ? (
            <EmptyState
              icon="👥"
              title="No customer types yet"
              description="Add one yourself or create examples to get started."
              action={
                <Button variant="primary" onClick={generateSeedPersonas} loading={isGenerating}>
                  Create example personas
                </Button>
              }
            />
          ) : (
            <div className="section-grid" style={{ marginTop: "var(--space-lg)" }}>
              {personas.map((persona) => (
                <div key={persona.id} className="card" style={{ display: "flex", flexDirection: "column" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: "var(--space-md)" }}>
                      <h4 style={{ margin: 0 }}>{persona.name}</h4>
                      <input
                        type="checkbox"
                        checked={persona.is_active}
                        onChange={() => togglePersona(persona.id, persona.is_active)}
                        style={{ cursor: "pointer", width: 18, height: 18 }}
                        title={persona.is_active ? "Click to deactivate" : "Click to activate"}
                      />
                    </div>
                    <p style={{ color: "var(--muted)", marginBottom: "var(--space-md)" }}>{persona.summary}</p>
                    <div className="badge-row" style={{ marginBottom: "var(--space-md)" }}>
                      {persona.role && <span className="badge">{persona.role}</span>}
                      <span className={`badge ${persona.source === "generated" ? "badge-success" : ""}`}>
                        {persona.source === "generated" ? "✨ AI-Generated" : "👤 Manual"}
                      </span>
                      {!persona.is_active && <span className="badge">Inactive</span>}
                    </div>
                  </div>
                  <div className="action-row" style={{ marginTop: "var(--space-md)" }}>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setDraft(persona);
                        setIsEditingId(persona.id);
                      }}
                      style={{ flex: 1 }}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => setDeleteId(persona.id)}
                      style={{ flex: 1 }}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <ConfirmModal
        open={deleteId !== null}
        onClose={() => setDeleteId(null)}
        onConfirm={deletePersona}
        title="Delete customer type"
        message={`Are you sure you want to delete "${personas.find((p) => p.id === deleteId)?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        danger
        loading={isDeleting}
      />

      <Drawer
        open={isEditingId !== null}
        onClose={() => {
          setIsEditingId(null);
          setDraft(emptyPersona);
        }}
        title="Edit Customer Type"
        footer={
          <div className="action-row" style={{ justifyContent: "flex-end" }}>
            <Button variant="secondary" onClick={() => setIsEditingId(null)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={updatePersona} loading={isUpdating}>
              Save Changes
            </Button>
          </div>
        }
      >
        <form onSubmit={(e) => { e.preventDefault(); updatePersona(e); }}>
          <label className="field">
            <span>Customer type</span>
            <input
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </label>

          <label className="field">
            <span>Job title or role</span>
            <input
              value={draft.role}
              onChange={(event) => setDraft({ ...draft, role: event.target.value })}
            />
          </label>

          <label className="field">
            <span>What do they want?</span>
            <textarea
              value={draft.summary}
              onChange={(event) => setDraft({ ...draft, summary: event.target.value })}
              rows={4}
            />
          </label>
        </form>
      </Drawer>
    </div>
  );
}
