"use client";

import { useEffect, useState } from "react";

import { Modal, ConfirmModal } from "@/components/modal";
import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import { Button, EmptyState, Spinner, Tabs } from "@/components/ui";
import { type PromptTemplate, apiRequest } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/lib/use-selected-project";

type PromptType = "reply" | "post" | "analysis";

interface EditingTemplate extends Partial<PromptTemplate> {
  id: number;
}

const PROMPT_TYPE_COPY: Record<PromptType, { label: string; description: string }> = {
  reply: {
    label: "Reply Systems",
    description: "Templates for discussion replies, comment responses, and community-native conversation handling.",
  },
  post: {
    label: "Original Posts",
    description: "Templates for educational posts, perspective-led content, and original thread creation.",
  },
  analysis: {
    label: "Analysis",
    description: "Templates that explain why a conversation matters, what risk exists, and how to respond.",
  },
};

export default function PromptsPage() {
  const { token } = useAuth();
  const toast = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState<number | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<EditingTemplate | null>(null);
  const [showDrawer, setShowDrawer] = useState(false);
  const [activeTab, setActiveTab] = useState<PromptType>("reply");
  const [projectId, setProjectId] = useState<number | null>(null);
  const [newTemplate, setNewTemplate] = useState({
    prompt_type: "reply" as PromptType,
    name: "",
    system_prompt: "",
    instructions: "",
  });

  useEffect(() => {
    if (!token) {
      return;
    }
    void loadTemplates();
  }, [token, selectedProjectId]);

  async function loadTemplates() {
    setLoading(true);
    try {
      const dashboard = await fetchDashboard(token!, selectedProjectId);
      const currentProject = getCurrentProject(dashboard);
      if (!currentProject) {
        setProjectId(null);
        setTemplates([]);
        setLoading(false);
        return;
      }
      setProjectId(currentProject.id);
      const rows = await apiRequest<PromptTemplate[]>(`/v1/prompts?project_id=${currentProject.id}`, {}, token);
      setTemplates(rows);
    } catch (error: any) {
      toast.error("Failed to load prompts", error.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveTemplate(template: EditingTemplate) {
    if (!token || !template.name || !template.system_prompt) {
      toast.error("Validation failed", "Name and system prompt are required.");
      return;
    }

    setSaving(true);
    try {
      const updated = await apiRequest<PromptTemplate>(
        `/v1/prompts/${template.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            prompt_type: template.prompt_type || "reply",
            name: template.name,
            system_prompt: template.system_prompt,
            instructions: template.instructions || "",
            is_default: template.is_default || false,
          }),
        },
        token
      );
      setTemplates((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
      toast.success("Template saved");
      setShowDrawer(false);
      setEditingTemplate(null);
    } catch (error: any) {
      toast.error("Save failed", error.message);
    } finally {
      setSaving(false);
    }
  }

  async function createTemplate() {
    if (!token || !projectId || !newTemplate.name || !newTemplate.system_prompt) {
      toast.error("Validation failed", "Name and system prompt are required.");
      return;
    }

    setSaving(true);
    try {
      const created = await apiRequest<PromptTemplate>(
        `/v1/prompts?project_id=${projectId}`,
        {
          method: "POST",
          body: JSON.stringify({
            prompt_type: newTemplate.prompt_type,
            name: newTemplate.name,
            system_prompt: newTemplate.system_prompt,
            instructions: newTemplate.instructions || "",
            is_default: false,
          }),
        },
        token
      );
      setTemplates((rows) => [...rows, created]);
      toast.success("Template created");
      setShowCreateModal(false);
      setNewTemplate({ prompt_type: activeTab, name: "", system_prompt: "", instructions: "" });
    } catch (error: any) {
      toast.error("Create failed", error.message);
    } finally {
      setSaving(false);
    }
  }

  async function duplicateTemplate(template: PromptTemplate) {
    if (!token || !projectId) {
      return;
    }

    setSaving(true);
    try {
      const duplicated = await apiRequest<PromptTemplate>(
        `/v1/prompts?project_id=${projectId}`,
        {
          method: "POST",
          body: JSON.stringify({
            prompt_type: template.prompt_type,
            name: `${template.name} (Copy)`,
            system_prompt: template.system_prompt,
            instructions: template.instructions,
            is_default: false,
          }),
        },
        token
      );
      setTemplates((rows) => [...rows, duplicated]);
      toast.success("Template duplicated");
    } catch (error: any) {
      toast.error("Duplicate failed", error.message);
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
      toast.success("Template deleted");
      setShowDeleteModal(null);
    } catch (error: any) {
      toast.error("Delete failed", error.message);
    } finally {
      setDeleting(null);
    }
  }

  const filteredTemplates = templates.filter((template) => template.prompt_type === activeTab);
  const activeCopy = PROMPT_TYPE_COPY[activeTab];

  return (
    <div style={{ display: "grid", gap: 24 }}>
      <section className="card">
        <div className="eyebrow">Template Systems</div>
        <h2 style={{ marginBottom: 8 }}>{activeCopy.label}</h2>
        <p>{activeCopy.description}</p>
        <div className="action-row" style={{ marginTop: 20 }}>
          <Button
            onClick={() => {
              setNewTemplate({ prompt_type: activeTab, name: "", system_prompt: "", instructions: "" });
              setShowCreateModal(true);
            }}
            variant="primary"
          >
            Create Template
          </Button>
        </div>
      </section>

      <Tabs
        tabs={[
          { key: "reply", label: "Reply", count: templates.filter((item) => item.prompt_type === "reply").length },
          { key: "post", label: "Post", count: templates.filter((item) => item.prompt_type === "post").length },
          { key: "analysis", label: "Analysis", count: templates.filter((item) => item.prompt_type === "analysis").length },
        ]}
        active={activeTab}
        onChange={(key) => setActiveTab(key as PromptType)}
      />

      {loading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}>
          <Spinner />
        </div>
      )}

      {!loading && filteredTemplates.length > 0 && (
        <div className="section-grid">
          {filteredTemplates.map((template) => (
            <div
              key={template.id}
              className="card"
              style={{ cursor: "pointer" }}
              onClick={() => {
                setEditingTemplate(template);
                setShowDrawer(true);
              }}
            >
              <div style={{ marginBottom: "1rem" }}>
                <h3 style={{ margin: "0 0 0.5rem 0", fontSize: "1.1rem" }}>{template.name}</h3>
                <div className="badge-row">
                  {template.is_default && <span className="badge">Default</span>}
                  <span className="badge">{template.prompt_type}</span>
                </div>
              </div>

              <p
                style={{
                  margin: 0,
                  fontSize: "0.9rem",
                  lineHeight: "1.5",
                  display: "-webkit-box",
                  WebkitLineClamp: 4,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {template.system_prompt}
              </p>
            </div>
          ))}
        </div>
      )}

      {!loading && filteredTemplates.length === 0 && (
        <EmptyState
          title={`No ${activeTab} templates yet`}
          description={`Create your first ${activeTab} template so the workflow can support more than a single reply mode.`}
        />
      )}

      {showCreateModal && (
        <Modal
          open={showCreateModal}
          title="Create Template"
          onClose={() => {
            setShowCreateModal(false);
            setNewTemplate({ prompt_type: activeTab, name: "", system_prompt: "", instructions: "" });
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            <div className="field">
              <label className="field-label">Template Type</label>
              <select
                value={newTemplate.prompt_type}
                onChange={(event) => setNewTemplate({ ...newTemplate, prompt_type: event.target.value as PromptType })}
              >
                <option value="reply">Reply</option>
                <option value="post">Post</option>
                <option value="analysis">Analysis</option>
              </select>
            </div>

            <div className="field">
              <label className="field-label">Template Name</label>
              <input
                type="text"
                value={newTemplate.name}
                onChange={(event) => setNewTemplate({ ...newTemplate, name: event.target.value })}
                placeholder="Example: High-signal expert reply"
              />
            </div>

            <div className="field">
              <label className="field-label">System Prompt</label>
              <textarea
                value={newTemplate.system_prompt}
                onChange={(event) => setNewTemplate({ ...newTemplate, system_prompt: event.target.value })}
                placeholder="Define the core writing rules, structure, and quality bar..."
                rows={7}
              />
            </div>

            <div className="field">
              <label className="field-label">Extra Instructions</label>
              <textarea
                value={newTemplate.instructions}
                onChange={(event) => setNewTemplate({ ...newTemplate, instructions: event.target.value })}
                placeholder="Add project-specific constraints, phrasing guidance, or review rules..."
                rows={4}
              />
            </div>

            <div className="action-row">
              <Button onClick={() => void createTemplate()} disabled={saving} variant="primary">
                {saving ? "Creating..." : "Create Template"}
              </Button>
              <Button onClick={() => setShowCreateModal(false)} variant="secondary">
                Cancel
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {showDrawer && editingTemplate && (
        <div className="drawer-overlay" onClick={() => setShowDrawer(false)}>
          <div className="drawer" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-header">
              <h2 style={{ margin: 0 }}>Edit Template</h2>
              <button className="modal-close" onClick={() => setShowDrawer(false)}>
                x
              </button>
            </div>

            <div className="drawer-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                <div className="field">
                  <label className="field-label">Template Type</label>
                  <select
                    value={editingTemplate.prompt_type || "reply"}
                    onChange={(event) => setEditingTemplate({ ...editingTemplate, prompt_type: event.target.value as PromptType })}
                  >
                    <option value="reply">Reply</option>
                    <option value="post">Post</option>
                    <option value="analysis">Analysis</option>
                  </select>
                </div>

                <div className="field">
                  <label className="field-label">Template Name</label>
                  <input
                    type="text"
                    value={editingTemplate.name || ""}
                    onChange={(event) => setEditingTemplate({ ...editingTemplate, name: event.target.value })}
                  />
                </div>

                <div className="field">
                  <label className="field-label">System Prompt</label>
                  <textarea
                    value={editingTemplate.system_prompt || ""}
                    onChange={(event) => setEditingTemplate({ ...editingTemplate, system_prompt: event.target.value })}
                    rows={8}
                  />
                </div>

                <div className="field">
                  <label className="field-label">Extra Instructions</label>
                  <textarea
                    value={editingTemplate.instructions || ""}
                    onChange={(event) => setEditingTemplate({ ...editingTemplate, instructions: event.target.value })}
                    rows={6}
                  />
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <div className="action-row">
                <Button onClick={() => void saveTemplate(editingTemplate)} disabled={saving} variant="primary">
                  {saving ? "Saving..." : "Save Template"}
                </Button>
                <Button onClick={() => void duplicateTemplate(editingTemplate as PromptTemplate)} disabled={saving} variant="secondary">
                  Duplicate
                </Button>
                <Button onClick={() => setShowDeleteModal(editingTemplate.id)} variant="danger">
                  Delete
                </Button>
                <Button onClick={() => setShowDrawer(false)} variant="ghost">
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showDeleteModal !== null && (
        <ConfirmModal
          open={showDeleteModal !== null}
          title="Delete Template"
          message="Are you sure you want to delete this template? This action cannot be undone."
          onConfirm={() => deleteTemplate(showDeleteModal)}
          onClose={() => setShowDeleteModal(null)}
          loading={deleting === showDeleteModal}
          confirmText="Delete"
          danger
        />
      )}
    </div>
  );
}
