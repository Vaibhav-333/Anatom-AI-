import { create } from "zustand";
import { persist } from "zustand/middleware";

export type NotificationType =
  | "report_analyzed"
  | "report_generated"
  | "plan_generated"
  | "plan_error"
  | "symptom_logged"
  | "medication_added"
  | "dose_logged"
  | "insights_ready"
  | "doctor_saved"
  | "export_ready";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  timestamp: number;
  read: boolean;
}

interface NotificationState {
  notifications: AppNotification[];
  addNotification: (type: NotificationType, title: string, body: string) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  remove: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set) => ({
      notifications: [],
      addNotification: (type, title, body) =>
        set((s) => ({
          notifications: [
            {
              id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
              type,
              title,
              body,
              timestamp: Date.now(),
              read: false,
            },
            ...s.notifications.slice(0, 49),
          ],
        })),
      markRead: (id) =>
        set((s) => ({
          notifications: s.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          ),
        })),
      markAllRead: () =>
        set((s) => ({
          notifications: s.notifications.map((n) => ({ ...n, read: true })),
        })),
      remove: (id) =>
        set((s) => ({
          notifications: s.notifications.filter((n) => n.id !== id),
        })),
      clearAll: () => set({ notifications: [] }),
    }),
    { name: "anatom-notifications" }
  )
);
