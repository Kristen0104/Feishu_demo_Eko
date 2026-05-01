import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { SessionStatus } from "@/types/session";

export type SessionFilter = "all" | "chat" | "doc" | "canvas" | "recent" | "starred";

type RuntimeSessionPatch = {
  status?: SessionStatus;
  updatedAt?: string;
};

type AppStore = {
  isLoggedIn: boolean;
  loginEmail: string | null;
  activeFilter: SessionFilter;
  selectedSessionId: string | null;
  isDetailOpen: boolean;
  starredMap: Record<string, boolean>;
  runtimeSessionMap: Record<string, RuntimeSessionPatch>;
  setLogin: (email: string) => void;
  logout: () => void;
  setActiveFilter: (filter: SessionFilter) => void;
  selectSession: (id: string) => void;
  closeDetail: () => void;
  initializeStars: (stars: Record<string, boolean>) => void;
  toggleStar: (id: string) => void;
  setRuntimeSessionPatch: (id: string, patch: RuntimeSessionPatch) => void;
};

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      isLoggedIn: false,
      loginEmail: null,
      activeFilter: "all",
      selectedSessionId: null,
      isDetailOpen: true,
      starredMap: {},
      runtimeSessionMap: {},
      setLogin: (email) =>
        set({
          isLoggedIn: true,
          loginEmail: email.toLowerCase(),
        }),
      logout: () =>
        set({
          isLoggedIn: false,
          loginEmail: null,
        }),
      setActiveFilter: (filter) => set({ activeFilter: filter }),
      selectSession: (id) =>
        set({
          selectedSessionId: id,
          isDetailOpen: true,
        }),
      closeDetail: () => set({ isDetailOpen: false }),
      initializeStars: (stars) => {
        const current = get().starredMap;
        const merged = { ...stars, ...current };
        set({ starredMap: merged });
      },
      toggleStar: (id) =>
        set((state) => ({
          starredMap: {
            ...state.starredMap,
            [id]: !state.starredMap[id],
          },
        })),
      setRuntimeSessionPatch: (id, patch) =>
        set((state) => ({
          runtimeSessionMap: {
            ...state.runtimeSessionMap,
            [id]: {
              ...state.runtimeSessionMap[id],
              ...patch,
            },
          },
        })),
    }),
    {
      name: "eko-app-store",
      partialize: (state) => ({
        isLoggedIn: state.isLoggedIn,
        loginEmail: state.loginEmail,
        activeFilter: state.activeFilter,
        selectedSessionId: state.selectedSessionId,
        isDetailOpen: state.isDetailOpen,
        starredMap: state.starredMap,
      }),
    },
  ),
);

