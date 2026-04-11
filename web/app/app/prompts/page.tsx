"use client";

import { useEffect, useState } from "react";

import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
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
import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { getErrorMessage } from "@/types/errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";
import { type PromptTemplate, apiRequest } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PageHeader } from "@/components/shared/page-header";

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
    } catch (error: unknown) {
      toast.error("Failed to load prompts", getErrorMessage(error));
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
    } catch (error: unknown) {
      toast.error("Save failed", getErrorMessage(error));
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
    } catch (error: unknown) {
      toast.error("Create failed", getErrorMessage(error));
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
    } catch (error: unknown) {
      toast.error("Duplicate failed", getErrorMessage(error));
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
    } catch (error: unknown) {
      toast.error("Delete failed", getErrorMessage(error));
    } finally {
      setDeleting(null);
    }
  }

  const filteredTemplates = templates.filter((template) => template.prompt_type === activeTab);
  const activeCopy = PROMPT_TYPE_COPY[activeTab];

  // Precompute tab counts once per render
  const replyCount = templates.filter((item) => item.prompt_type === "reply").length;
  const postCount = templates.filter((item) => item.prompt_type === "post").length;
  const analysisCount = templates.filter((item) => item.prompt_type === "analysis").length;

  return (
    <div className="grid gap-8">
      <PageHeader
        title="Prompt Templates"
        description={activeCopy.description}
        actions={
          <Button
            onClick={() => {
              setNewTemplate({ prompt_type: activeTab, name: "", system_prompt: "", instructions: "" });
              setShowCreateModal(true);
            }}
          >
            Create Template
          </Button>
        }
        tabs={
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as PromptType)}>
            <TabsList>
              <TabsTrigger value="reply">
                Reply
                {replyCount > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-xs">
                    {replyCount}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="post">
                Post
                {postCount > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-xs">
                    {postCount}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="analysis">
                Analysis
                {analysisCount > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-xs">
                    {analysisCount}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        }
      />

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as PromptType)}>
        <TabsContent value={activeTab}>
          {loading && (
            <div className="flex justify-center p-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {!loading && filteredTemplates.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTemplates.map((template) => (
                <div
                  key={template.id}
                  className="cursor-pointer rounded-xl border bg-card p-5 transition-all hover:shadow-md hover:border-primary/30"
                  onClick={() => {
                    setEditingTemplate(template);
                    setShowDrawer(true);
                  }}
                >
                  <div className="mb-4">
                    <h3 className="mb-2 text-base font-semibold text-foreground">{template.name}</h3>
                    <div className="flex flex-wrap gap-2">
                      {template.is_default && <Badge variant="secondary">Default</Badge>}
                      <Badge variant="outline">{template.prompt_type}</Badge>
                    </div>
                  </div>

                  <p className="line-clamp-4 text-sm leading-relaxed text-muted-foreground">
                    {template.system_prompt}
                  </p>
                </div>
              ))}
            </div>
          )}

          {!loading && filteredTemplates.length === 0 && (
            <div className="mt-4 flex flex-col items-center justify-center p-8 text-center">
              <span className="mb-4 text-4xl">📝</span>
              <h3 className="mb-1 text-sm font-semibold text-foreground">No {activeTab} templates yet</h3>
              <p className="text-xs text-muted-foreground">
                Create your first {activeTab} template so the workflow can support more than a single reply mode.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Create Template Dialog */}
      <Dialog open={showCreateModal} onOpenChange={(open) => {
        if (!open) {
          setShowCreateModal(false);
          setNewTemplate({ prompt_type: activeTab, name: "", system_prompt: "", instructions: "" });
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Template</DialogTitle>
            <DialogDescription>
              Define a new prompt template for {activeTab} generation.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-5">
            <div className="grid gap-2">
              <Label>Template Type</Label>
              <Select
                value={newTemplate.prompt_type}
                onValueChange={(value) => setNewTemplate({ ...newTemplate, prompt_type: value as PromptType })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="reply">Reply</SelectItem>
                  <SelectItem value="post">Post</SelectItem>
                  <SelectItem value="analysis">Analysis</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="new-template-name">Template Name</Label>
              <Input
                id="new-template-name"
                type="text"
                value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="Example: High-signal expert reply"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="new-system-prompt">System Prompt</Label>
              <Textarea
                id="new-system-prompt"
                value={newTemplate.system_prompt}
                onChange={(e) => setNewTemplate({ ...newTemplate, system_prompt: e.target.value })}
                placeholder="Define the core writing rules, structure, and quality bar..."
                rows={7}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="new-instructions">Extra Instructions</Label>
              <Textarea
                id="new-instructions"
                value={newTemplate.instructions}
                onChange={(e) => setNewTemplate({ ...newTemplate, instructions: e.target.value })}
                placeholder="Add project-specific constraints, phrasing guidance, or review rules..."
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => void createTemplate()} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? "Creating..." : "Create Template"}
            </Button>
            <Button variant="outline" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Template Dialog (replaces drawer) */}
      <Dialog open={showDrawer} onOpenChange={setShowDrawer}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Template</DialogTitle>
            <DialogDescription>
              Modify the prompt template configuration.
            </DialogDescription>
          </DialogHeader>
          {editingTemplate && (
            <div className="grid gap-5">
              <div className="grid gap-2">
                <Label>Template Type</Label>
                <Select
                  value={editingTemplate.prompt_type || "reply"}
                  onValueChange={(value) => setEditingTemplate({ ...editingTemplate, prompt_type: value as PromptType })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reply">Reply</SelectItem>
                    <SelectItem value="post">Post</SelectItem>
                    <SelectItem value="analysis">Analysis</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit-template-name">Template Name</Label>
                <Input
                  id="edit-template-name"
                  type="text"
                  value={editingTemplate.name || ""}
                  onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit-system-prompt">System Prompt</Label>
                <Textarea
                  id="edit-system-prompt"
                  value={editingTemplate.system_prompt || ""}
                  onChange={(e) => setEditingTemplate({ ...editingTemplate, system_prompt: e.target.value })}
                  rows={8}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="edit-instructions">Extra Instructions</Label>
                <Textarea
                  id="edit-instructions"
                  value={editingTemplate.instructions || ""}
                  onChange={(e) => setEditingTemplate({ ...editingTemplate, instructions: e.target.value })}
                  rows={6}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => void saveTemplate(editingTemplate!)} disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? "Saving..." : "Save Template"}
            </Button>
            <Button
              variant="outline"
              onClick={() => void duplicateTemplate(editingTemplate as PromptTemplate)}
              disabled={saving}
            >
              Duplicate
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowDeleteModal(editingTemplate!.id)}
            >
              Delete
            </Button>
            <Button variant="ghost" onClick={() => setShowDrawer(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <AlertDialog open={showDeleteModal !== null} onOpenChange={(open) => { if (!open) setShowDeleteModal(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this template? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => void deleteTemplate(showDeleteModal!)}
              disabled={deleting === showDeleteModal}
            >
              {deleting === showDeleteModal && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
