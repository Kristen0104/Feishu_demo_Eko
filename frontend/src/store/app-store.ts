import { create } from "zustand";
import { persist } from "zustand/middleware";

import { clearAccessToken } from "@/lib/auth-token";
import { clearAuthStorage, saveAuthAfterLogin } from "@/lib/auth-session";
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
  /** 会话详情页左侧「对话」栏是否展开（由侧栏「会话」旁箭头同步） */
  sessionDetailChatOpen: boolean;
  starredMap: Record<string, boolean>;
  runtimeSessionMap: Record<string, RuntimeSessionPatch>;
  setLogin: (email: string, options?: { remember?: boolean; fromStorage?: boolean }) => void;
  logout: () => void;
  setActiveFilter: (filter: SessionFilter) => void;
  selectSession: (id: string) => void;
  closeDetail: () => void;
  toggleSessionDetailChatOpen: () => void;
  setSessionDetailChatOpen: (open: boolean) => void;
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
      sessionDetailChatOpen: true,
      starredMap: {},
      runtimeSessionMap: {},
      setLogin: (email, options) => {
        const normalized = email.toLowerCase();
        if (options?.fromStorage) {
          set({ isLoggedIn: true, loginEmail: normalized });
          return;
        }
        if (typeof window !== "undefined" && !options?.fromStorage) {
          saveAuthAfterLogin(normalized, options?.remember ?? true);
        }
        set({ isLoggedIn: true, loginEmail: normalized });
      },
      logout: () => {
        if (typeof window !== "undefined") {
          clearAuthStorage();
          clearAccessToken();
        }
        set({
          isLoggedIn: false,
          loginEmail: null,
        });
      },
      setActiveFilter: (filter) => set({ activeFilter: filter }),
      selectSession: (id) =>
        set({
          selectedSessionId: id,
          isDetailOpen: true,
        }),
      closeDetail: () => set({ isDetailOpen: false }),
      toggleSessionDetailChatOpen: () =>
        set((state) => ({ sessionDetailChatOpen: !state.sessionDetailChatOpen })),
      setSessionDetailChatOpen: (open) => set({ sessionDetailChatOpen: open }),
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
      version: 3,
      migrate: (persisted, fromVersion) => {
        try {
          if (
            fromVersion < 2 &&
            persisted &&
            typeof persisted === "object" &&
            persisted !== null &&
            "state" in persisted
          ) {
            const wrap = persisted as { state: Record<string, unknown> };
            if (wrap.state) {
              delete wrap.state.isLoggedIn;
              delete wrap.state.loginEmail;
            }
          }
          if (
            fromVersion < 3 &&
            persisted &&
            typeof persisted === "object" &&
            persisted !== null &&
            "state" in persisted
          ) {
            const wrap = persisted as { state: Record<string, unknown> };
            if (wrap.state && typeof wrap.state.sessionDetailChatOpen !== "boolean") {
              wrap.state.sessionDetailChatOpen = true;
            }
          }
        } catch {
          /* ignore corrupted persisted payloads */
        }
        return persisted;
      },
      partialize: (state) => ({
        activeFilter: state.activeFilter,
        selectedSessionId: state.selectedSessionId,
        isDetailOpen: state.isDetailOpen,
        sessionDetailChatOpen: state.sessionDetailChatOpen,
        starredMap: state.starredMap,
      }),
    },
  ),
);

