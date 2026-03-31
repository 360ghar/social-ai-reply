import { apiRequest } from "../api";

export async function forgotPassword(email: string) {
  return apiRequest<{ ok: boolean }>(
    `/v1/auth/forgot-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }
  );
}

export async function resetPassword(token: string, password: string) {
  return apiRequest<{ ok: boolean; message: string }>(
    `/v1/auth/reset-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token, password }) }
  );
}
