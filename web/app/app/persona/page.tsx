"use client";

import { FormEvent, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

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
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from "@/components/ui/sheet";
import { apiRequest, type Dashboard, type Persona } from "@/lib/api";
import { fetchDashboard, getCurrentProject } from "@/lib/workspace-data";
import { useSelectedProjectId } from "@/hooks/use-selected-project";

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
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isEditingId, setIsEditingId] = useState<number | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
    setIsLoading(true);
    apiRequest<Persona[]>(`/v1/personas?project_id=${project.id}`, {}, token)
      .then((data) => {
        setPersonas(data);
        setIsLoading(false);
      })
      .catch((err) => {
        error("Failed to load personas", err.message);
        setIsLoading(false);
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

  const activeCount = personas.filter((p) => p.is_active).length;
  const aiCount = personas.filter((p) => p.source === "generated").length;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="text-center">
            <div className="text-2xl font-semibold">{personas.length}</div>
            <div className="text-xs text-muted-foreground">Total Personas</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <div className="text-2xl font-semibold">{activeCount}</div>
            <div className="text-xs text-muted-foreground">Active</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center">
            <div className="text-2xl font-semibold">{aiCount}</div>
            <div className="text-xs text-muted-foreground">AI-Generated</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardContent>
            <form onSubmit={createPersona}>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Customers</p>
              <h2 className="text-lg font-semibold mt-1">Who do you want to help on Reddit?</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Write 2 or 3 customer types in simple language. Example: Small business owner looking for a better CRM.
              </p>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="persona-name">Customer type</Label>
                  <Input
                    id="persona-name"
                    value={draft.name}
                    onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                    placeholder="e.g., 'Small business owner'"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-role">Job title or role</Label>
                  <Input
                    id="persona-role"
                    value={draft.role}
                    onChange={(event) => setDraft({ ...draft, role: event.target.value })}
                    placeholder="e.g., 'Marketing Manager'"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="persona-summary">What do they want?</Label>
                  <Textarea
                    id="persona-summary"
                    value={draft.summary}
                    onChange={(event) => setDraft({ ...draft, summary: event.target.value })}
                    placeholder="Describe what this customer type needs or wants..."
                    rows={3}
                  />
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mt-6">
                <Button variant="secondary" type="submit" disabled={isCreating}>
                  {isCreating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save customer type
                </Button>
                <Button
                  type="button"
                  onClick={generateSeedPersonas}
                  disabled={isGenerating}
                >
                  {isGenerating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Create examples
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Saved customers</p>
            <h2 className="text-lg font-semibold mt-1">People you want to reach</h2>
            {personas.length === 0 ? (
              <div className="flex flex-col items-center justify-center p-8 text-center">
                <span className="text-4xl mb-4">👥</span>
                <h3 className="text-base font-semibold mb-1">No customer types yet</h3>
                <p className="text-sm text-muted-foreground mb-4">Add one yourself or create examples to get started.</p>
                <Button onClick={generateSeedPersonas} disabled={isGenerating}>
                  {isGenerating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Create example personas
                </Button>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-4 mt-6">
                {personas.map((persona) => (
                  <div key={persona.id} className="rounded-lg border bg-card p-4 flex flex-col">
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="text-sm font-semibold">{persona.name}</h4>
                        <input
                          type="checkbox"
                          checked={persona.is_active}
                          onChange={() => togglePersona(persona.id, persona.is_active)}
                          className="h-[18px] w-[18px] cursor-pointer"
                          title={persona.is_active ? "Click to deactivate" : "Click to activate"}
                        />
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{persona.summary}</p>
                      <div className="flex flex-wrap gap-2 mb-3">
                        {persona.role && <Badge variant="secondary">{persona.role}</Badge>}
                        <Badge variant={persona.source === "generated" ? "default" : "outline"}>
                          {persona.source === "generated" ? "AI-Generated" : "Manual"}
                        </Badge>
                        {!persona.is_active && <Badge variant="outline">Inactive</Badge>}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Button
                        variant="secondary"
                        className="flex-1"
                        onClick={() => {
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
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="destructive"
                        className="flex-1"
                        onClick={() => setDeleteId(persona.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

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

      <Sheet
        open={isEditingId !== null}
        onOpenChange={(open) => {
          if (!open) {
            setIsEditingId(null);
            setDraft(emptyPersona);
          }
        }}
      >
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>Edit Customer Type</SheetTitle>
          </SheetHeader>
          <form onSubmit={(e) => { void updatePersona(e); }} className="space-y-4 p-4">
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
          <SheetFooter>
            <div className="flex justify-end gap-2 w-full">
              <Button variant="secondary" onClick={() => { setIsEditingId(null); setDraft(emptyPersona); }}>
                Cancel
              </Button>
              <Button onClick={() => void submitPersonaUpdate()} disabled={isUpdating}>
                {isUpdating && <Loader2 className="h-4 w-4 animate-spin" />}
                Save Changes
              </Button>
            </div>
          </SheetFooter>
        </SheetContent>
      </Sheet>
    </div>
  );
}
