"use client";

import { useEffect, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getVoiceProfiles, type VoiceProfile } from "@/lib/api/voice";
import { cn } from "@/lib/utils";

interface VoiceProfileSelectProps {
  token: string | null | undefined;
  projectId: number | null | undefined;
  value: number | null;
  onChange: (profileId: number | null) => void;
  className?: string;
}

/**
 * Compact voice-profile picker used next to reply-generation actions.
 * Auto-selects the project's default profile once profiles load.
 * Renders nothing when the project has no voice profiles.
 */
export function VoiceProfileSelect({ token, projectId, value, onChange, className }: VoiceProfileSelectProps) {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!token || !projectId) {
      return;
    }
    let cancelled = false;
    setLoaded(false);
    getVoiceProfiles(token, projectId)
      .then((rows) => {
        if (cancelled) return;
        setProfiles(rows);
        setLoaded(true);
      })
      .catch(() => {
        // Non-blocking: reply generation works without a voice profile.
        if (cancelled) return;
        setProfiles([]);
        setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [token, projectId]);

  // Default to the project's is_default profile when nothing is selected yet.
  useEffect(() => {
    if (!loaded || value !== null) {
      return;
    }
    const defaultProfile = profiles.find((profile) => profile.is_default);
    if (defaultProfile) {
      onChange(defaultProfile.id);
    }
  }, [loaded, profiles, value, onChange]);

  if (!loaded || profiles.length === 0) {
    return null;
  }

  return (
    <Select
      value={value !== null ? String(value) : ""}
      onValueChange={(next) => {
        const parsed = Number(next);
        onChange(Number.isInteger(parsed) && parsed > 0 ? parsed : null);
      }}
    >
      <SelectTrigger className={cn("h-8 min-w-[10rem] text-xs", className)} aria-label="Voice profile">
        <SelectValue placeholder="Voice profile" />
      </SelectTrigger>
      <SelectContent>
        {profiles.map((profile) => (
          <SelectItem key={profile.id} value={String(profile.id)}>
            {profile.name}
            {profile.is_default ? " (default)" : ""}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
