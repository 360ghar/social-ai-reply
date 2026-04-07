import { supabase } from "@/lib/supabase";
import { apiRequest } from "../api";

/**
 * Request a password reset email via Supabase.
 * Supabase sends the email with a magic link that redirects back to the app.
 */
export async function forgotPassword(email: string): Promise<{ ok: boolean }> {
  const redirectTo = `${window.location.origin}/reset-password`;
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo,
  });
  if (error) {
    throw new Error(error.message);
  }
  return { ok: true };
}

/**
 * Update password using the Supabase session that was established
 * when the user clicked the reset link in their email.
 */
export async function resetPassword(_token: string, password: string): Promise<{ ok: boolean; message: string }> {
  // After clicking the reset link, Supabase sets a session automatically.
  // We use that session to update the password.
  const { error } = await supabase.auth.updateUser({ password });
  if (error) {
    throw new Error(error.message);
  }
  return { ok: true, message: "Password updated. You can now log in." };
}
