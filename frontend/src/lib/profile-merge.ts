import type { UserProfile } from "@/types/profile";

export function mergeProfile(base: UserProfile, overrides: Partial<UserProfile>): UserProfile {
  const merged: UserProfile = {
    ...base,
    ...overrides,
    languages: overrides.languages ?? base.languages,
  };
  return merged;
}

/** 将「中文 · English」一类文案解析为语言列表 */
export function parseLanguages(input: string): string[] {
  return input
    .split(/[·•,，、;；]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function deriveInitials(displayName: string, nameEn: string): string {
  const d = displayName.trim();
  if (d) {
    const segs = d.split(/\s+/);
    if (segs.length >= 2 && segs[0] && segs[1])
      return (segs[0].charAt(0) + segs[1].charAt(0)).toUpperCase();
    if (d.length >= 2) return d.slice(0, 2).toUpperCase();
    return (d.charAt(0) + (nameEn.trim().charAt(0) || "")).toUpperCase();
  }
  const e = nameEn.trim();
  if (e) {
    const parts = e.split(/\s+/);
    if (parts.length >= 2 && parts[0] && parts[1])
      return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
    return e.slice(0, 2).toUpperCase();
  }
  return "ME";
}
