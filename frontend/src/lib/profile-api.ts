import { readAccessToken } from "@/lib/auth-token";
import { apiUrl, fetchEkoJson, type EkoApiEnvelope } from "@/lib/eko-api";
import { deriveInitials } from "@/lib/profile-merge";
import type { UserProfile } from "@/types/profile";

export type AuthMeUser = {
  user_id: string;
  display_name: string;
  name_en?: string | null;
  feishu_user_id: string;
  email?: string | null;
  avatar_url?: string | null;
  feishu_bound?: boolean;
  union_id?: string | null;
  phone?: string | null;
  phone_ext?: string | null;
  location?: string | null;
  time_zone?: string | null;
  employee_id?: string | null;
  job_title?: string | null;
  department?: string | null;
  team?: string | null;
  reports_to?: string | null;
  joined_at?: string | null;
  bio?: string | null;
  languages?: string[];
};

export function resolveAvatarUrl(value?: string | null): string {
  const raw = value?.trim() ?? "";
  if (!raw) return "";
  if (/^(https?:|data:|blob:)/i.test(raw)) return raw;
  return apiUrl(raw);
}

export async function fetchCurrentAuthUser(): Promise<AuthMeUser> {
  return fetchEkoJson<AuthMeUser>("/api/v1/auth/me", { cache: "no-store" });
}

export async function updateCurrentAuthUser(patch: Partial<UserProfile>): Promise<AuthMeUser> {
  return fetchEkoJson<AuthMeUser>("/api/v1/auth/me", {
    method: "PATCH",
    body: JSON.stringify(profilePatchToAuthPayload(patch)),
  });
}

export async function uploadCurrentUserAvatar(file: File): Promise<string> {
  const form = new FormData();
  form.set("file", file);

  const headers = new Headers();
  const token = readAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(apiUrl("/api/v1/auth/me/avatar"), {
    method: "POST",
    headers,
    body: form,
  });

  const json = (await res.json().catch(() => null)) as
    | EkoApiEnvelope<{ avatar_url: string }>
    | { detail?: string; message?: string }
    | null;
  if (!json || !("code" in json)) {
    const detail = json && "detail" in json && typeof json.detail === "string" ? json.detail : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  if (!res.ok || json.code !== 0) {
    throw new Error(json.message || `HTTP ${res.status}`);
  }
  return json.data.avatar_url;
}

export async function updateCurrentPassword(currentPassword: string, newPassword: string): Promise<AuthMeUser> {
  return fetchEkoJson<AuthMeUser>("/api/v1/auth/me/password", {
    method: "PATCH",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export type FeishuLoginUrlResult = {
  authorize_url: string;
  state: string;
  expires_in: number;
};

export async function createFeishuBindUrl(redirectUri: string): Promise<FeishuLoginUrlResult> {
  return fetchEkoJson<FeishuLoginUrlResult>(
    `/api/v1/auth/feishu/login-url?redirect_uri=${encodeURIComponent(redirectUri)}`,
    { cache: "no-store" },
  );
}

export async function bindFeishuWithCallbackUrl(callbackUrl: string, redirectUri: string): Promise<AuthMeUser> {
  const parsed = new URL(callbackUrl.trim());
  const code = parsed.searchParams.get("code");
  const state = parsed.searchParams.get("state");
  if (!code || !state) {
    throw new Error("回跳链接里没有 code/state，请复制飞书授权后的完整地址。");
  }
  return fetchEkoJson<AuthMeUser>("/api/v1/auth/feishu/bind", {
    method: "POST",
    body: JSON.stringify({ code, state, redirect_uri: redirectUri }),
  });
}

export function authUserToProfilePatch(user: AuthMeUser): Partial<UserProfile> {
  const displayName = user.display_name?.trim() || user.email?.trim() || "Eko User";
  const email = user.email?.trim() || "";
  const nameEn = user.name_en?.trim() || displayName;
  return {
    displayName,
    nameEn,
    initials: deriveInitials(displayName, nameEn),
    avatarUrl: resolveAvatarUrl(user.avatar_url),
    email,
    phone: user.phone?.trim() || "",
    phoneExt: user.phone_ext?.trim() || "",
    location: user.location?.trim() || "",
    timeZone: user.time_zone?.trim() || "",
    employeeId: user.employee_id?.trim() || "",
    jobTitle: user.job_title?.trim() || "",
    department: user.department?.trim() || "",
    team: user.team?.trim() || "",
    reportsTo: user.reports_to?.trim() || "",
    joinedAt: user.joined_at?.trim() || "",
    bio: user.bio?.trim() || "",
    languages: user.languages?.length ? user.languages : [],
  };
}

function profilePatchToAuthPayload(patch: Partial<UserProfile>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (patch.displayName !== undefined) payload.display_name = patch.displayName;
  if (patch.nameEn !== undefined) payload.name_en = patch.nameEn;
  if (patch.email !== undefined) payload.email = patch.email;
  if (patch.avatarUrl !== undefined) payload.avatar_url = patch.avatarUrl;
  if (patch.phone !== undefined) payload.phone = patch.phone;
  if (patch.phoneExt !== undefined) payload.phone_ext = patch.phoneExt;
  if (patch.location !== undefined) payload.location = patch.location;
  if (patch.timeZone !== undefined) payload.time_zone = patch.timeZone;
  if (patch.employeeId !== undefined) payload.employee_id = patch.employeeId;
  if (patch.jobTitle !== undefined) payload.job_title = patch.jobTitle;
  if (patch.department !== undefined) payload.department = patch.department;
  if (patch.team !== undefined) payload.team = patch.team;
  if (patch.reportsTo !== undefined) payload.reports_to = patch.reportsTo;
  if (patch.joinedAt !== undefined) payload.joined_at = patch.joinedAt;
  if (patch.bio !== undefined) payload.bio = patch.bio;
  if (patch.languages !== undefined) payload.languages = patch.languages;
  return payload;
}
