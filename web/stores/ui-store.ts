import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  notifPanelOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setNotifPanelOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  notifPanelOpen: false,
  toggleSidebar() {
    set((s) => ({ sidebarOpen: !s.sidebarOpen }));
  },
  setSidebarOpen(open) {
    set({ sidebarOpen: open });
  },
  setNotifPanelOpen(open) {
    set({ notifPanelOpen: open });
  },
}));
