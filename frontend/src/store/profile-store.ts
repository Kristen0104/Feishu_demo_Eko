import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { UserProfile } from "@/types/profile";

type ProfileStoreState = {
  /** Browser-side draft fields for the current authenticated profile. */
  profileOverrides: Partial<UserProfile>;
  profileOwnerEmail: string | null;
  lastSavedAt: string | null;
  setProfileOverrides: (patch: Partial<UserProfile>) => void;
  adoptProfileOwner: (email: string | null) => void;
  clearProfileState: () => void;
  markSaved: () => void;
  resetProfileOverrides: () => void;
};

export const useProfileStore = create<ProfileStoreState>()(
  persist(
    (set) => ({
      profileOverrides: {},
      profileOwnerEmail: null,
      lastSavedAt: null,
      setProfileOverrides: (patch) =>
        set((state) => ({
          profileOverrides: { ...state.profileOverrides, ...patch },
        })),
      adoptProfileOwner: (email) =>
        set((state) => {
          const normalized = email?.trim().toLowerCase() || null;
          if (state.profileOwnerEmail === normalized) {
            return {};
          }
          return {
            profileOwnerEmail: normalized,
            profileOverrides: {},
            lastSavedAt: null,
          };
        }),
      clearProfileState: () =>
        set({
          profileOverrides: {},
          profileOwnerEmail: null,
          lastSavedAt: null,
        }),
      markSaved: () =>
        set({
          lastSavedAt: new Date().toLocaleString("zh-CN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          }),
        }),
      resetProfileOverrides: () => set({ profileOverrides: {}, lastSavedAt: null }),
    }),
    {
      name: "eko-profile-store",
      partialize: (s) => ({
        profileOverrides: s.profileOverrides,
        profileOwnerEmail: s.profileOwnerEmail,
        lastSavedAt: s.lastSavedAt,
      }),
    },
  ),
);
