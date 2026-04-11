import { apiRequest } from "../api";

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  body: string | null;
  action_url: string | null;
  is_read: boolean;
  created_at: string | null;
}

export async function getNotifications(token: string, unreadOnly = false) {
  return apiRequest<{ items: NotificationItem[]; total: number; unread_count: number }>(
    `/v1/notifications?unread_only=${unreadOnly}`, { headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function markNotificationRead(token: string, id: number) {
  return apiRequest<{ ok: boolean }>(
    `/v1/notifications/${id}/read`, { method: "PUT", headers: { Authorization: `Bearer ${token}` } }
  );
}

export async function markAllNotificationsRead(token: string) {
  return apiRequest<{ ok: boolean }>(
    `/v1/notifications/read-all`, { method: "PUT", headers: { Authorization: `Bearer ${token}` } }
  );
}
