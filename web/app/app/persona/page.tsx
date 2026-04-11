"use client";

import { FormEvent, useEffect, useState } from "react";
import { Loader2, Users, Sparkles, MoreHorizontal } from "lucide-react";

import { useAuth } from "@/components/auth/auth-provider";
import { useToast } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { apiRequest, type Dashboard, type Persona } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";
import { PageHeader } from "@/components/shared/page-header";
import { KPIGrid, type KPICardProps } from "@/components/shared/kpi-card";
import { EmptyState } from "@/components/shared/empty-state";

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
  const { success, error, warning } = useToast();
  const selectedProjectId = useSelectedProjectId();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [draft, setDraft] = useState(emptyPersona);
  const [loading, setLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEditingId, setIsEditingId] = useState<number | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);

  const project = dashboard ? getCurrentProject(dashboard) : null;

  useEffect(() => {
    if (!token) {
      return;
    }
    fetchDashboard(token, selectedProjectId)
      .then(setDashboard)
      .catch((err) => {
        error("Failed to load", err.message);
      });
  }, [token, error, selectedProjectId]);

  useEffect(() => {
    if (!token || !project) {
      return;
    }
    setLoading(true);
    apiRequest<Persona[]>(`/v1/personas?project_id=${project.id}`, {}, token)
      .then((data) => {
        setPersonas(data);
        setLoading(false);
      })
      .catch((err) => {
        error("Failed to load personas", err.message);
        setLoading(false);
      });
  }, [project, token, error]);

  async function createPersona(event: FormEvent) {
    event.preventDefault();
    if (!token || !project) {
      return;
    }
    if (!draft.name.trim()) {
      warning("Required field", "Please enter a customer type name.");
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
      setShowCreateDialog(false);
      success("Saved", "Customer type has been created.");
    } catch (err) {
      error("Save failed", err instanceof Error ? err.message : "Could not save the customer type.");
    } finally {
      setIsCreating(false);
    }
  }

  async function updatePersona(event: FormEvent) {
    event.preventDefault();
    await submitPersonaUpdate();
  }

  async function submitPersonaUpdate() {
    if (!token || isEditingId === null) {
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
      success("Saved", "Customer type has been updated.");
    } catch (err) {
      error("Update failed", err instanceof Error ? err.message : "Could not update the customer type.");
    } finally {
      setIsUpdating(false);
    }
  }

  async function togglePersona(personaId: number, currentActive: boolean) {
    if (!token) return;
    try {
      const persona = personas.find((p) => p.id === personaId);
      if (!persona) return;
      const updated = await apiRequest<Persona>(`/v1/personas/${personaId}`, {
        method: "PUT",
        body: JSON.stringify({ ...persona, is_active: !currentActive })
      }, token);
      setPersonas((rows) => rows.map((p) => (p.id === personaId ? updated : p)));
      success(
        !currentActive ? "Activated" : "Deactivated",
        `Customer type "${persona.name}" is now ${!currentActive ? "active" : "inactive"}.`
      );
    } catch (err) {
      error("Failed", err instanceof Error ? err.message : "Could not update status.");
    }
  }

  async function deletePersona() {
    if (!token || deleteId === null) return;
    setIsDeleting(true);
    try {
      const persona = personas.find((p) => p.id === deleteId);
      await apiRequest(`/v1/personas/${deleteId}`, {
        method: "DELETE"
      }, token);
      setPersonas((rows) => rows.filter((p) => p.id !== deleteId));
      setDeleteId(null);
      success("Deleted", `Customer type "${persona?.name}" has been removed.`);
    } catch (err) {
      error("Delete failed", err instanceof Error ? err.message : "Could not delete the customer type.");
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
      success("Created", "Example customer types have been generated.");
    } catch (err) {
      error("Generation failed", err instanceof Error ? err.message : "Could not create example customer types.");
    } finally {
      setIsGenerating(false);
    }
  }

  function openEditDialog(persona: Persona) {
    setDraft({
      name: persona.name,
      role: persona.role ?? "",
      summary: persona.summary,
      pain_points: persona.pain_points,
      goals: persona.goals,
      triggers: persona.triggers,
      preferred_subreddits: persona.preferred_subreddits,
      source: persona.source,
      is_active: persona.is_active,
    });
    setIsEditingId(persona.id);
    setMenuOpenId(null);
  }

  const activeCount = personas.filter((p) => p.is_active).length;
  const aiCount = personas.filter((p) => p.source === "generated").length;

  const kpiCards: KPICardProps[] = [
    { label: "Total Personas", value: personas.length, icon: Users },
    { label: "Active", value: activeCount },
    { label: "AI-Generated", value: aiCount, icon: Sparkles },
  ];

  if (loading) {
    return (
      <div className="space-y-8">
        <div className="grid grid-cols-3 gap-5">
          <Card><CardContent><Skeleton className="h-20 w-full rounded-lg" /></CardContent></Card>
          <Card><CardContent><Skeleton className="h-20 w-full rounded-lg" /></CardContent></Card>
          <Card><CardContent><Skeleton className="h-20 w-full rounded-lg" /></CardContent></Card>
        </div>
        <Card><CardContent><Skeleton className="h-40 w-full rounded-lg" /></CardContent></Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Personas"
        description="Define who you want to help on Reddit"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              onClick={generateSeedPersonas}
              disabled={isGenerating}
            >
              {isGenerating && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Examples
            </Button>
            <Button onClick={() => { setDraft(emptyPersona); setShowCreateDialog(true); }}>
              Add Persona
            </Button>
          </div>
        }
      />

      <KPIGrid cards={kpiCards} columns={3} />

      {/* Persona List */}
      {personas.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No customer types yet"
          description="Add one yourself or create examples to get started."
          action={{ label: "Create example personas", onClick: generateSeedPersonas }}
        />
      ) : (
        <div className="grid gap-3">
          {personas.map((persona) => (
            <Card key={persona.id} className="transition-all hover:shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <h3 className="text-sm font-semibold text-foreground truncate">{persona.name}</h3>
                      {persona.role && <Badge variant="secondary" className="shrink-0">{persona.role}</Badge>}
                      <Badge variant={persona.source === "generated" ? "default" : "outline"} className="shrink-0">
                        {persona.source === "generated" ? "AI" : "Manual"}
                      </Badge>
                    </div>
                    {persona.summary && (
                      <p className="text-sm text-muted-foreground line-clamp-2">{persona.summary}</p>
                    )}
                  </div>

                  {/* Right side: toggle + actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {/* Active toggle */}
                    <button
                      type="button"
                      role="switch"
                      aria-checked={persona.is_active}
                      onClick={() => togglePersona(persona.id, persona.is_active)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors ${
                        persona.is_active ? "bg-primary" : "bg-muted"
                      }`}
                      title={persona.is_active ? "Click to deactivate" : "Click to activate"}
                    >
                      <span
                        className={`pointer-events-none block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${
                          persona.is_active ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </button>

                    {/* Action menu */}
                    <div className="relative">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setMenuOpenId(menuOpenId === persona.id ? null : persona.id)}
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                      {menuOpenId === persona.id && (
                        <>
                          <div className="fixed inset-0 z-40" onClick={() => setMenuOpenId(null)} />
                          <div className="absolute right-0 top-8 z-50 w-32 rounded-lg border bg-popover p-1 shadow-md">
                            <button
                              className="flex w-full items-center rounded-md px-2.5 py-1.5 text-sm hover:bg-muted text-left"
                              onClick={() => openEditDialog(persona)}
                            >
                              Edit
                            </button>
                            <button
                              className="flex w-full items-center rounded-md px-2.5 py-1.5 text-sm text-destructive hover:bg-destructive/10 text-left"
                              onClick={() => { setDeleteId(persona.id); setMenuOpenId(null); }}
                            >
                              Delete
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create Persona Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={(open) => { if (!open) { setShowCreateDialog(false); setDraft(emptyPersona); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Persona</DialogTitle>
            <DialogDescription>Describe a customer type you want to reach on Reddit.</DialogDescription>
          </DialogHeader>
          <form id="create-persona-form" onSubmit={(e) => void createPersona(e)} className="grid gap-4">
            <div className="space-y-2">
              <Label htmlFor="create-name">Customer type</Label>
              <Input
                id="create-name"
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                placeholder="e.g., 'Small business owner'"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-role">Job title or role</Label>
              <Input
                id="create-role"
                value={draft.role}
                onChange={(event) => setDraft({ ...draft, role: event.target.value })}
                placeholder="e.g., 'Marketing Manager'"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="create-summary">What do they want?</Label>
              <Textarea
                id="create-summary"
                value={draft.summary}
                onChange={(event) => setDraft({ ...draft, summary: event.target.value })}
                placeholder="Describe what this customer type needs or wants..."
                rows={3}
              />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowCreateDialog(false); setDraft(emptyPersona); }}>
              Cancel
            </Button>
            <Button type="submit" form="create-persona-form" disabled={isCreating}>
              {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Persona Dialog */}
      <Dialog open={isEditingId !== null} onOpenChange={(open) => { if (!open) { setIsEditingId(null); setDraft(emptyPersona); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Customer Type</DialogTitle>
            <DialogDescription>Update the details for this persona.</DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => void updatePersona(e)} className="grid gap-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Customer type</Label>
              <Input
                id="edit-name"
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role">Job title or role</Label>
              <Input
                id="edit-role"
                value={draft.role}
                onChange={(event) => setDraft({ ...draft, role: event.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-summary">What do they want?</Label>
              <Textarea
                id="edit-summary"
                value={draft.summary}
                onChange={(event) => setDraft({ ...draft, summary: event.target.value })}
                rows={4}
              />
            </div>
          </form>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsEditingId(null); setDraft(emptyPersona); }}>
              Cancel
            </Button>
            <Button onClick={() => void submitPersonaUpdate()} disabled={isUpdating}>
              {isUpdating && <Loader2 className="h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={(open) => { if (!open) setDeleteId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete customer type</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &quot;{personas.find((p) => p.id === deleteId)?.name}&quot;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={deletePersona} disabled={isDeleting}>
              {isDeleting && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
