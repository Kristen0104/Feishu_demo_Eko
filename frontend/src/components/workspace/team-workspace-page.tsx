"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { WorkspacePageHeader } from "@/components/workspace/workspace-page-framing";
import { authUserToProfilePatch, fetchCurrentAuthUser } from "@/lib/profile-api";
import { fetchTeamMembers, inviteTeamMember, removeTeamMember } from "@/lib/team-api";
import type { TeamMember } from "@/types/team";

const TEAM_NAME = "默认团队";

function initialsFor(member: TeamMember): string {
  const source = member.displayName?.trim() || member.email;
  const parts = source.split(/[\s@._-]+/).filter(Boolean);
  if (parts.length === 0) return "T";
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);
}

function statusLabel(member: TeamMember): string {
  if (member.role === "owner") return "负责人";
  if (member.status === "invited") return "待加入";
  return "成员";
}

export function TeamWorkspacePage() {
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [currentUserPatch, setCurrentUserPatch] = useState<{ email?: string; displayName?: string; avatarUrl?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteError, setInviteError] = useState("");
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const memberCount = members.length;
  const activeCount = useMemo(() => members.filter((member) => member.status === "active").length, [members]);
  const displayMembers = useMemo(
    () =>
      members.map((member) => {
        if (!member.isCurrentUser || !currentUserPatch) return member;
        return {
          ...member,
          displayName: currentUserPatch.displayName || member.displayName,
          email: currentUserPatch.email || member.email,
          avatarUrl: currentUserPatch.avatarUrl || member.avatarUrl,
        };
      }),
    [currentUserPatch, members],
  );

  async function loadMembers() {
    try {
      const data = await fetchTeamMembers();
      setMembers(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载团队成员失败。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const data = await fetchTeamMembers();
        if (cancelled) return;
        setMembers(data);
        setError("");
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "加载团队成员失败。");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    void fetchCurrentAuthUser()
      .then((user) => {
        if (cancelled) return;
        const patch = authUserToProfilePatch(user);
        setCurrentUserPatch({
          email: patch.email,
          displayName: patch.displayName,
          avatarUrl: patch.avatarUrl,
        });
      })
      .catch(() => {
        /* Keep member list data when auth profile is unavailable. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleInviteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = inviteEmail.trim().toLowerCase();
    if (!normalized || !normalized.includes("@")) {
      setInviteError("请输入有效邮箱。");
      return;
    }

    setInviteSubmitting(true);
    setInviteError("");
    try {
      await inviteTeamMember(normalized);
      setInviteEmail("");
      setInviteOpen(false);
      await loadMembers();
    } catch (e) {
      setInviteError(e instanceof Error ? e.message : "邀请失败。");
    } finally {
      setInviteSubmitting(false);
    }
  }

  async function handleRemove(member: TeamMember) {
    if (member.role === "owner") return;
    const confirmed = window.confirm(`确定将 ${member.displayName || member.email} 移出团队吗？`);
    if (!confirmed) return;

    setRemovingId(member.id);
    setError("");
    try {
      await removeTeamMember(member.id);
      setMembers((current) => current.filter((item) => item.id !== member.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "移除成员失败。");
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-white">
      <WorkspacePageHeader
        title="团队"
        description={`当前空间：${TEAM_NAME} · ${memberCount} 名成员 · ${activeCount} 人已加入`}
        actions={
          <button
            type="button"
            onClick={() => {
              setInviteError("");
              setInviteOpen(true);
            }}
            className="min-h-10 w-full rounded-[12px] bg-blue-600 px-4 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-blue-700 sm:w-auto"
          >
            邀请成员
          </button>
        }
      />

      <div className="min-h-0 flex-1 overflow-auto px-3 py-4 sm:px-5 lg:px-7 lg:py-6">
        {error ? (
          <div className="mb-4 rounded-[14px] border border-rose-200 bg-rose-50 px-4 py-3 text-[13px] text-rose-700">
            {error}
          </div>
        ) : null}

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => (
              <div
                key={`team-skeleton-${index}`}
                className="h-[92px] animate-pulse rounded-[18px] border border-slate-200/90 bg-slate-50"
              />
            ))}
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {displayMembers.map((member) => (
              <div
                key={member.id}
                className="flex min-w-0 flex-col gap-3 rounded-[18px] border border-slate-200/90 bg-white p-4 shadow-[0_4px_18px_rgba(15,23,42,0.04)] sm:flex-row sm:items-center"
              >
                <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[14px] font-semibold text-slate-700">
                  {member.avatarUrl ? (
                    <Image
                      src={member.avatarUrl}
                      alt={member.displayName || member.email}
                      width={48}
                      height={48}
                      unoptimized
                      className="h-full w-full rounded-full object-cover"
                    />
                  ) : (
                    initialsFor(member)
                  )}
                  <span
                    className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-white ${
                      member.status === "active" ? "bg-emerald-500" : "bg-amber-400"
                    }`}
                  />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-[14px] font-semibold text-slate-950">
                        {member.displayName || member.email}
                      </p>
                      <p className="truncate text-[12px] text-slate-500">{member.email}</p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                        member.role === "owner"
                          ? "bg-blue-50 text-blue-700"
                          : member.status === "invited"
                            ? "bg-amber-50 text-amber-800"
                            : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {statusLabel(member)}
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-white px-2.5 py-0.5 text-[11px] font-semibold text-slate-600 ring-1 ring-slate-200">
                      {member.role === "owner" ? "负责人" : "成员"}
                    </span>
                    {member.invitedByName ? (
                      <span className="text-[11px] text-slate-400">由 {member.invitedByName} 邀请</span>
                    ) : null}
                    {member.isCurrentUser ? (
                      <span className="text-[11px] font-medium text-blue-600">我</span>
                    ) : null}
                  </div>
                </div>

                {member.role !== "owner" ? (
                  <button
                    type="button"
                    onClick={() => void handleRemove(member)}
                    disabled={removingId === member.id}
                    className="w-full rounded-[10px] border border-slate-200 bg-white px-2.5 py-1.5 text-[12px] font-semibold text-slate-600 transition hover:border-rose-200 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                  >
                    {removingId === member.id ? "移除中" : "移除"}
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>

      {inviteOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4">
          <div className="w-full max-w-md rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(15,23,42,0.22)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-[18px] font-semibold tracking-[-0.03em] text-slate-950">邀请成员</h2>
                <p className="mt-1 text-[13px] text-slate-500">输入邮箱，已有账号会直接加入，未注册则先进入待邀请状态。</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setInviteOpen(false);
                  setInviteEmail("");
                  setInviteError("");
                }}
                className="rounded-full px-2 py-1 text-[14px] text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
              >
                ×
              </button>
            </div>

            <form className="mt-5 space-y-4" onSubmit={handleInviteSubmit}>
              <label className="block">
                <span className="mb-1.5 block text-[13px] font-medium text-slate-500">邮箱</span>
                <input
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="teammate@company.com"
                  className="h-[48px] w-full rounded-[14px] border border-slate-200 px-4 text-[14px] text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
                />
              </label>

              {inviteError ? (
                <div className="rounded-[12px] border border-rose-200 bg-rose-50 px-3 py-2 text-[13px] text-rose-700">
                  {inviteError}
                </div>
              ) : null}

              <div className="flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setInviteOpen(false);
                    setInviteEmail("");
                    setInviteError("");
                  }}
                  className="rounded-[12px] border border-slate-200 bg-white px-4 py-2 text-[13px] font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={inviteSubmitting}
                  className="rounded-[12px] bg-blue-600 px-4 py-2 text-[13px] font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {inviteSubmitting ? "邀请中" : "发送邀请"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
