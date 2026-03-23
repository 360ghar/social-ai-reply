"use client";

import { useEffect, useState } from "react";

import { Button, EmptyState, Spinner } from "../../../components/ui";
import { Modal, ConfirmModal } from "../../../components/modal";
import { useToast } from "../../../components/toast";
import { useAuth } from "../../../components/auth-provider";
import { apiRequest, type Dashboard, type PromptTemplate } from "../../../lib/api";
import { fetchDashboard, getCurrentProject } from "../../../lib/workspace-data";

interface EditingTemplate extends Partial<PromptTemplate> {
  id: number;
}

export default function PromptsPage() {
  const { token } = useAuth();
  const { toast } = useToast();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState<number | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<EditingTemplate | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    system_prompt: "",
    instructions: "",
  });

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token)
      .then(setDashboard)
      .catch((err) => {
        toast({ type: "error", message: err.message });
        setLoading(false);
      });
  }, [token, toast]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setLoading(true);
    apiRequest<PromptTemplate[]>(`/v1/prompts?project_id=${project.id}`, {}, token)
      .then(setTemplates)
      .catch((err) => {
        toast({ type: "error", message: err.message });
      })
      .finally(() => setLoading(false));
  }, [project, token, toast]);

  async function saveTemplate(template: EditingTemplate) {
    if (!token || !template.name || !template.system_prompt) {
      toast({ type: "error", message: "Name and system prompt are required" });
      return;
    }

    setSaving(true);
    try {
      const updated = await apiRequest<PromptTemplate>(
        `/v1/prompts/${template.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            name: template.name,
            system_prompt: template.system_prompt,
            instructions: template.instructions || "",
          }),
        },
        token
      );
      setTemplates((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      toast({ type: "success", message: "Template saved successfully" });
      setShowDrawer(false);
      setEditingTemplate(null);
    } catch (err) {
      toast({ type: "error", message: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function createTemplate() {
    if (!token || !project || !newTemplate.name || !newTemplate.system_prompt) {
      toast({ type: "error", message: "Name and system prompt are required" });
      return;
    }

    setSaving(true);
    try {
      const created = await apiRequest<PromptTemplate>(
        `/v1/prompts`,
        {
          method: "POST",
          body: JSON.stringify({
            project_id: project.id,
            prompt_type: "custom",
            name: newTemplate.name,
            system_prompt: newTemplate.system_prompt,
            instructions: newTemplate.instructions || "",
          }),
        },
        token
      );
      setTemplates((rows) => [...rows, created]);
      toast({ type: "success", message: "Template created successfully" });
      setShowCreateModal(false);
      setNewTemplate({ name: "", system_prompt: "", instructions: "" });
    } catch (err) {
      toast({ type: "error", message: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function duplicateTemplate(template: PromptTemplate) {
    if (!token || !project) {
      return;
    }

    setSaving(true);
    try {
      const duplicated = await apiRequest<PromptTemplate>(
        `/v1/prompts`,
        {
          method: "POST",
          body: JSON.stringify({
            project_id: project.id,
            prompt_type: template.prompt_type,
            name: `${template.name} (Copy)`,
            system_prompt: template.system_prompt,
            instructions: template.instructions,
          }),
        },
        token
      );
      setTemplates((rows) => [...rows, duplicated]);
      toast({ type: "success", message: "Template duplicated successfully" });
    } catch (err) {
      toast({ type: "error", message: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function deleteTemplate(id: number) {
    if (!token) {
      return;
    }

    setDeleting(id);
    try {
      await apiRequest(`/v1/prompts/${id}`, { method: "DELETE" }, token);
      setTemplates((rows) => rows.filter((row) => row.id !== id));
      toast({ type: "success", message: "Template deleted successfully" });
      setShowDeleteModal(null);
    } catch (err) {
      toast({ type: "error", message: (err as Error).message });
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
      {/* Header Section */}
      <section className="card">
        <div className="eyebrow">Reply Templates</div>
        <h2>Customize how AI drafts are written</h2>
        <p>Create and manage reply templates to define the writing style and tone for AI-generated responses.</p>

        <div className="action-row" style={{ marginTop: "1.5rem" }}>
          <Button onClick={() => setShowCreateModal(true)} variant="primary">
            Create Template
          </Button>
        </div>
      </section>

      {/* Loading State */}
      {loading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
          <Spinner />
        </div>
      )}

      {/* Templates Grid */}
      {!loading && templates.length > 0 && (
        <div className="section-grid">
          {templates.map((template) => (
            <div
              key={template.id}
              className="card"
              style={{
                cursor: "pointer",
                transition: "box-shadow 0.2s",
              }}
              onClick={() => {
                setEditingTemplate(template);
                setShowDrawer(true);
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.boxShadow = "";
              }}
            >
              <div style={{ marginBottom: "1rem" }}>
                <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem" }}>{template.name}</h3>
                {template.is_default && <span className="badge">Default</span>}
              </div>

              <p
                style={{
                  margin: "0 0 1rem 0",
                  fontSize: "0.9rem",
                  color: "var(--text-secondary)",
                  lineHeight: "1.4",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  display: "-webkit-box",
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: "vertical",
                }}
              >
                {template.system_prompt}
              </p>

              <div className="badge-row">
                <span className="badge">{template.prompt_type}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && templates.length === 0 && (
        <EmptyState
          title="No reply templates yet"
          description="Create your first template to customize how AI drafts are written."
        />
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <Modal
          title="Create Reply Template"
          onClose={() => {
            setShowCreateModal(false);
            setNewTemplate({ name: "", system_prompt: "", instructions: "" });
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div className="field">
              <label>
                <span>Template Name</span>
                <input
                  type="text"
                  value={newTemplate.name}
                  onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                  placeholder="e.g., Professional Tone"
                />
              </label>
            </div>

            <div className="field">
              <label>
                <span>System Prompt</span>
                <textarea
                  value={newTemplate.system_prompt}
                  onChange={(e) => setNewTemplate({ ...newTemplate, system_prompt: e.target.value })}
                  placeholder="Define the core writing rules and style..."
                  rows={6}
                />
              </label>
            </div>

            <div className="field">
              <label>
                <span>Extra Instructions (optional)</span>
                <textarea
                  value={newTemplate.instructions}
                  onChange={(e) => setNewTemplate({ ...newTemplate, instructions: e.target.value })}
                  placeholder="Additional guidelines and constraints..."
                  rows={4}
                />
              </label>
            </div>

            <div className="action-row">
              <Button
                onClick={() => createTemplate()}
                disabled={saving}
                variant="primary"
              >
                {saving ? "Creating..." : "Create Template"}
              </Button>
              <Button
                onClick={() => {
                  setShowCreateModal(false);
                  setNewTemplate({ name: "", system_prompt: "", instructions: "" });
                }}
                variant="secondary"
              >
                Cancel
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Edit Drawer */}
      {showDrawer && editingTemplate && (
        <div className="drawer-overlay" onClick={() => setShowDrawer(false)}>
          <div
            className="drawer"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="drawer-header">
              <h2 style={{ margin: 0 }}>Edit Reply Template</h2>
              <button
                className="modal-close"
                onClick={() => setShowDrawer(false)}
              >
                ×
              </button>
            </div>

            <div className="drawer-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                <div className="field">
                  <label>
                    <span>Template Name</span>
                    <input
                      type="text"
                      value={editingTemplate.name || ""}
                      onChange={(e) =>
                        setEditingTemplate({ ...editingTemplate, name: e.target.value })
                      }
                    />
                  </label>
                </div>

                <div className="field">
                  <label>
                    <span>System Prompt</span>
                    <textarea
                      value={editingTemplate.system_prompt || ""}
                      onChange={(e) =>
                        setEditingTemplate({
                          ...editingTemplate,
                          system_prompt: e.target.value,
                        })
                      }
                      rows={8}
                    />
                  </label>
                </div>

                <div className="field">
                  <label>
                    <span>Extra Instructions (optional)</span>
                    <textarea
                      value={editingTemplate.instructions || ""}
                      onChange={(e) =>
                        setEditingTemplate({
                          ...editingTemplate,
                          instructions: e.target.value,
                        })
                      }
                      rows={6}
                    />
                  </label>
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <div className="action-row">
                <Button
                  onClick={() => saveTemplate(editingTemplate)}
                  disabled={saving}
                  variant="primary"
                >
                  {saving ? "Saving..." : "Save Template"}
                </Button>
                <Button
                  onClick={() => duplicateTemplate(editingTemplate as PromptTemplate)}
                  disabled={saving}
                  variant="secondary"
                >
                  Duplicate
                </Button>
                <Button
                  onClick={() => setShowDeleteModal(editingTemplate.id)}
                  variant="danger"
                >
                  Delete
                </Button>
                <Button
                  onClick={() => setShowDrawer(false)}
                  variant="ghost"
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal !== null && (
        <ConfirmModal
          title="Delete Template"
          message="Are you sure you want to delete this template? This action cannot be undone."
          onConfirm={() => deleteTemplate(showDeleteModal)}
          onCancel={() => setShowDeleteModal(null)}
          isLoading={deleting === showDeleteModal}
          confirmText="Delete"
          cancelText="Cancel"
        />
      )}
    </div>
  );
}
