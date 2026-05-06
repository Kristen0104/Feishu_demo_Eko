"use client";

import { useEffect, useMemo, useState } from "react";

import { EditableTextRow, SectionCard } from "@/components/profile/profile-blocks";
import { deriveInitials, mergeProfile, parseLanguages } from "@/lib/profile-merge";
import { authUserToProfilePatch, fetchCurrentAuthUser, updateCurrentAuthUser } from "@/lib/profile-api";
import { useProfileStore } from "@/store/profile-store";
import type { UserProfile } from "@/types/profile";

export function ProfileOverview({ base }: { base: UserProfile }) {
  const profileOverrides = useProfileStore((s) => s.profileOverrides);
  const setProfileOverrides = useProfileStore((s) => s.setProfileOverrides);
  const adoptProfileOwner = useProfileStore((s) => s.adoptProfileOwner);
  const markSaved = useProfileStore((s) => s.markSaved);
  const lastSavedAt = useProfileStore((s) => s.lastSavedAt);
  const [authPatch, setAuthPatch] = useState<Partial<UserProfile> | null>(null);
  const [authStatus, setAuthStatus] = useState<"loading" | "live" | "fallback">("loading");
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchCurrentAuthUser()
      .then((user) => {
        if (!alive) return;
        adoptProfileOwner(user.email?.trim().toLowerCase() || null);
        setAuthPatch(authUserToProfilePatch(user));
        setAuthStatus("live");
      })
      .catch(() => {
        if (!alive) return;
        setAuthStatus("fallback");
      });
    return () => {
      alive = false;
    };
  }, [adoptProfileOwner]);

  const serverBase = useMemo(() => mergeProfile(base, authPatch ?? {}), [authPatch, base]);
  const data = useMemo(() => mergeProfile(serverBase, profileOverrides), [profileOverrides, serverBase]);

  const commit = async (patch: Partial<UserProfile>) => {
    const nextPatch =
      patch.displayName !== undefined
        ? {
            ...patch,
            initials: deriveInitials(patch.displayName, patch.nameEn ?? data.nameEn),
          }
        : patch.nameEn !== undefined
          ? {
              ...patch,
              initials: deriveInitials(data.displayName, patch.nameEn),
            }
          : patch;

    setSaveStatus("正在保存...");
    try {
      const user = await updateCurrentAuthUser(nextPatch);
      const livePatch = authUserToProfilePatch(user);
      setAuthPatch(livePatch);
      setProfileOverrides({});
      markSaved();
      setSaveStatus("已保存到后端账号资料");
    } catch (error) {
      setProfileOverrides(nextPatch);
      markSaved();
      setSaveStatus(error instanceof Error ? `后端保存失败，已暂存本机：${error.message}` : "后端保存失败，已暂存本机");
    }
  };

  const patchLanguagesFromText = (text: string) => {
    void commit({ languages: parseLanguages(text) });
  };

  return (
    <>
      <section className="overflow-hidden rounded-[24px] border border-white/80 bg-white/95 shadow-[0_20px_56px_rgba(15,23,42,0.08)] backdrop-blur-sm">
        <div className="flex flex-col gap-6 border-b border-slate-100 px-6 py-8 sm:flex-row sm:items-center">
          <div className="relative mx-auto shrink-0 sm:mx-0">
            <div className="flex h-[104px] w-[104px] items-center justify-center rounded-full bg-gradient-to-br from-slate-100 to-slate-200 text-[28px] font-semibold text-slate-700 shadow-inner">
              {data.initials}
            </div>
            <span className="absolute bottom-1 right-1 h-4 w-4 rounded-full border-[3px] border-white bg-emerald-500 shadow-sm" title="在线" />
            <button
              type="button"
              className="absolute -bottom-1 -right-1 flex h-9 w-9 cursor-not-allowed items-center justify-center rounded-full border border-slate-200 bg-white text-[11px] font-semibold text-slate-400 shadow-md"
              disabled
              title="演示：接入头像上传后可更换"
            >
              更换
            </button>
          </div>
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <h1 className="text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{data.displayName}</h1>
            <p className="mt-1 text-[14px] text-slate-500">{data.nameEn}</p>
            <p className="mt-3 truncate text-[14px] font-medium text-slate-700">{data.email}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[12px] font-medium text-slate-600">
                {data.jobTitle}
              </span>
              <span className="rounded-full border border-blue-100 bg-blue-50/90 px-3 py-1 text-[12px] font-medium text-blue-600">
                {data.team}
              </span>
            </div>
            {lastSavedAt ? (
              <p className="mt-3 text-[12px] text-slate-400">上次保存 · {lastSavedAt}</p>
            ) : null}
            <p className="mt-2 text-[12px] text-slate-400">
              {authStatus === "live"
                ? "身份来源：后端 /api/v1/auth/me；编辑会保存到账号资料"
                : authStatus === "loading"
                  ? "正在读取后端登录身份…"
                  : "身份来源：本地兜底资料；未读到后端登录身份"}
            </p>
            {saveStatus ? <p className="mt-2 text-[12px] text-blue-500">{saveStatus}</p> : null}
          </div>
        </div>
      </section>

      <SectionCard title="基本信息" description="姓名与偏好信息会保存到后端账号资料；离线或接口异常时才暂存本机。">
        <EditableTextRow
          label="姓名"
          value={data.displayName}
          onSave={(v) => void commit({ displayName: v })}
        />
        <EditableTextRow
          label="别名 / 英文名"
          value={data.nameEn}
          onSave={(v) => void commit({ nameEn: v })}
        />
        <EditableTextRow label="个人简介" value={data.bio} multiline onSave={(v) => void commit({ bio: v })} />
        <EditableTextRow
          label="界面语言"
          value={data.languages.join(" · ")}
          hint="使用「·」或逗号分隔多种语言。"
          onSave={patchLanguagesFromText}
        />
      </SectionCard>

      <SectionCard title="联系方式" description="手机号与邮箱将用于通知与安全校验。">
        <EditableTextRow
          label="工作邮箱"
          value={data.email}
          hint="生产环境通常由组织开通，不可随意修改。"
          onSave={(v) => void commit({ email: v })}
        />
        <EditableTextRow label="手机号码" value={data.phone} onSave={(v) => void commit({ phone: v })} />
        <EditableTextRow label="分机" value={data.phoneExt} hint="内线号码。" onSave={(v) => void commit({ phoneExt: v })} />
        <EditableTextRow label="常驻办公地" value={data.location} onSave={(v) => void commit({ location: v })} />
        <EditableTextRow label="时区" value={data.timeZone} onSave={(v) => void commit({ timeZone: v })} />
      </SectionCard>

      <SectionCard title="组织信息" description="当前由账号资料维护；后续接入人事主数据后可按字段设为只读。">
        <EditableTextRow label="工号" value={data.employeeId} onSave={(v) => void commit({ employeeId: v })} />
        <EditableTextRow label="部门" value={data.department} onSave={(v) => void commit({ department: v })} />
        <EditableTextRow label="职务" value={data.jobTitle} onSave={(v) => void commit({ jobTitle: v })} />
        <EditableTextRow label="所属团队" value={data.team} onSave={(v) => void commit({ team: v })} />
        <EditableTextRow label="直属上级" value={data.reportsTo} onSave={(v) => void commit({ reportsTo: v })} />
        <EditableTextRow label="入职日期" value={data.joinedAt} onSave={(v) => void commit({ joinedAt: v })} />
      </SectionCard>

      <div className="flex items-start gap-2 rounded-[18px] border border-slate-200/80 bg-white/60 px-4 py-3 text-[12px] text-slate-500">
        <svg viewBox="0 0 24 24" className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 3.5 5.8 6.1v5c0 4.2 2.4 7.9 6.2 9.4 3.8-1.5 6.2-5.2 6.2-9.4v-5L12 3.5Z" />
          <path d="m9.7 12.1 1.6 1.7 3.4-3.9" />
        </svg>
        <span>账号安全与通知偏好请使用左侧「账号与安全」「通知设置」。敏感字段接入后端后由权限策略控制可见范围。</span>
      </div>
    </>
  );
}
