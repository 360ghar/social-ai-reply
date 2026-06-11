import { apiRequest } from "../api";

/** A reusable writing-voice profile used to steer reply generation. */
export type VoiceProfile = {
  id: number;
  project_id: number;
  name: string;
  example_replies: string[];
  tone_descriptors: string[];
  banned_phrases: string[];
  style_guide: string | null;
  is_default: boolean;
  created_at: string | null;
  updated_at: string | null;
};

export type VoiceProfileCreatePayload = {
  name: string;
  example_replies?: string[];
  tone_descriptors?: string[];
  banned_phrases?: string[];
  style_guide?: string | null;
  is_default?: boolean;
};

export type VoiceProfileUpdatePayload = Partial<VoiceProfileCreatePayload>;

export async function getVoiceProfiles(token: string, projectId?: number | null): Promise<VoiceProfile[]> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<VoiceProfile[]>(`/v1/voice-profiles${qs}`, {}, token);
}

export async function createVoiceProfile(
  token: string,
  projectId: number | null | undefined,
  data: VoiceProfileCreatePayload,
): Promise<VoiceProfile> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiRequest<VoiceProfile>(
    `/v1/voice-profiles${qs}`,
    { method: "POST", body: JSON.stringify(data) },
    token,
  );
}

export async function updateVoiceProfile(
  token: string,
  profileId: number,
  data: VoiceProfileUpdatePayload,
): Promise<VoiceProfile> {
  return apiRequest<VoiceProfile>(
    `/v1/voice-profiles/${profileId}`,
    { method: "PUT", body: JSON.stringify(data) },
    token,
  );
}

export async function deleteVoiceProfile(token: string, profileId: number): Promise<void> {
  await apiRequest<{ ok: boolean }>(`/v1/voice-profiles/${profileId}`, { method: "DELETE" }, token);
}

/** Run the profile's example replies through the LLM to produce a style guide + tone descriptors. */
export async function analyzeVoiceProfile(token: string, profileId: number): Promise<VoiceProfile> {
  return apiRequest<VoiceProfile>(`/v1/voice-profiles/${profileId}/analyze`, { method: "POST" }, token);
}
