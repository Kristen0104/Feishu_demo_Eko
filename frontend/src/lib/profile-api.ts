import { fetchEkoJson } from "@/lib/eko-api";
import { deriveInitials } from "@/lib/profile-merge";
import type { UserProfile } from "@/types/profile";

export type AuthMeUser = {
  user_id: string;
  display_name: string;
  feishu_user_id: string;
  email?: string | null;
  avatar_url?: string | null;
};

export async function fetchCurrentAuthUser(): Promise<AuthMeUser> {
  return fetchEkoJson<AuthMeUser>("/api/v1/auth/me", { cache: "no-store" });
}

export function authUserToProfilePatch(user: AuthMeUser): Partial<UserProfile> {
  const displayName = user.display_name?.trim() || user.email?.trim() || "Eko User";
  const email = user.email?.trim() || "";
  return {
    displayName,
    nameEn: displayName,
    initials: deriveInitials(displayName, displayName),
    email,
  };
}
