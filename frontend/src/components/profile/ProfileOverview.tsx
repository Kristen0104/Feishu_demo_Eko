"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";

import { EditableTextRow, SectionCard } from "@/components/profile/profile-blocks";
import { deriveInitials, mergeProfile, parseLanguages } from "@/lib/profile-merge";
import {
  authUserToProfilePatch,
  fetchCurrentAuthUser,
  updateCurrentAuthUser,
  uploadCurrentUserAvatar,
} from "@/lib/profile-api";
import { useProfileStore } from "@/store/profile-store";
import type { UserProfile } from "@/types/profile";

export function ProfileOverview({ base }: { base: UserProfile }) {
  const router = useRouter();
  const profileOverrides = useProfileStore((s) => s.profileOverrides);
  const setProfileOverrides = useProfileStore((s) => s.setProfileOverrides);
  const adoptProfileOwner = useProfileStore((s) => s.adoptProfileOwner);
  const markSaved = useProfileStore((s) => s.markSaved);
  const lastSavedAt = useProfileStore((s) => s.lastSavedAt);
  const [authPatch, setAuthPatch] = useState<Partial<UserProfile> | null>(null);
  const [authStatus, setAuthStatus] = useState<"loading" | "live" | "unavailable">("loading");
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [avatarEditing, setAvatarEditing] = useState(false);
  const [avatarDraft, setAvatarDraft] = useState("");
  const [avatarFileName, setAvatarFileName] = useState("");
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

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
        setAuthStatus("unavailable");
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
      setSaveStatus("已保存");
      router.refresh();
    } catch (error) {
      setSaveStatus(error instanceof Error ? `保存失败：${error.message}` : "保存失败");
    }
  };

  const submitAvatar = () => {
    const next = avatarDraft.trim();
    void commit({ avatarUrl: next });
    setAvatarEditing(false);
    setAvatarFileName("");
    setAvatarError(null);
    setAvatarUploading(false);
  };

  const handleAvatarFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setAvatarError(null);
    if (!file.type.startsWith("image/")) {
      setAvatarError("请选择图片文件。");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarError("图片不能超过 5MB。");
      return;
    }

    setAvatarUploading(true);
    try {
      const nextAvatar = await uploadCurrentUserAvatar(file);
      setAvatarDraft(nextAvatar);
      setAvatarFileName(file.name);
    } catch (error) {
      setAvatarError(error instanceof Error ? error.message : "头像上传失败，请换一张图片。");
    } finally {
      setAvatarUploading(false);
    }
  };

  const patchLanguagesFromText = (text: string) => {
    void commit({ languages: parseLanguages(text) });
  };

  return (
    <>
      <section className="overflow-hidden rounded-[20px] border border-white/80 bg-white/95 shadow-[0_20px_56px_rgba(15,23,42,0.08)] backdrop-blur-sm sm:rounded-[24px]">
        <div className="flex flex-col gap-5 border-b border-slate-100 px-4 py-6 sm:flex-row sm:items-center sm:gap-6 sm:px-6 sm:py-8">
          <div className="relative mx-auto shrink-0 sm:mx-0">
            <div className="relative flex h-[104px] w-[104px] items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-slate-100 to-slate-200 text-[28px] font-semibold text-slate-700 shadow-inner">
              {data.avatarUrl ? (
                <Image
                  src={data.avatarUrl}
                  alt={`${data.displayName || "用户"}头像`}
                  fill
                  unoptimized
                  sizes="104px"
                  className="object-cover"
                />
              ) : (
                data.initials
              )}
            </div>
            <span className="absolute bottom-1 right-1 h-4 w-4 rounded-full border-[3px] border-white bg-emerald-500 shadow-sm" title="在线" />
          </div>
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <h1 className="text-[26px] font-semibold tracking-[-0.04em] text-slate-950">{data.displayName}</h1>
            <p className="mt-1 text-[14px] text-slate-500">{data.nameEn}</p>
            <p className="mt-3 break-words text-[14px] font-medium text-slate-700">{data.email}</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
              <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[12px] font-medium text-slate-600">
                {data.jobTitle}
              </span>
              <span className="rounded-full border border-blue-100 bg-blue-50/90 px-3 py-1 text-[12px] font-medium text-blue-600">
                {data.team}
              </span>
            </div>
            {lastSavedAt ? (
              <p className="mt-3 text-[12px] text-slate-400">已保存 · {lastSavedAt}</p>
            ) : null}
            <p className="mt-2 text-[12px] text-slate-400">
              {authStatus === "live"
                ? "资料已同步"
                : authStatus === "loading"
                  ? "正在读取账号资料..."
                  : "请重新登录后再编辑资料"}
            </p>
            {saveStatus ? <p className="mt-2 text-[12px] text-blue-500">{saveStatus}</p> : null}
          </div>
        </div>
      </section>

      <SectionCard title="基本信息" description="姓名与偏好会用于你的工作区展示。">
        <div className="border-b border-slate-100 py-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
            <div className="w-full shrink-0 text-[13px] font-medium text-slate-500 sm:w-[168px]">头像</div>
            <div className="min-w-0 flex-1">
              {!avatarEditing ? (
                <p className="break-words text-[15px] font-medium leading-[1.6] text-slate-900">
                  {data.avatarUrl ? "已设置图片头像" : "使用姓名首字母头像"}
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                    <label className="inline-flex w-fit cursor-pointer items-center rounded-[10px] border border-slate-200 bg-white px-3 py-2 text-[13px] font-semibold text-slate-700 hover:border-blue-200 hover:text-blue-600">
                      选择本机图片
                      <input type="file" accept="image/*" className="sr-only" onChange={handleAvatarFileChange} />
                    </label>
                    <span className="min-w-0 truncate text-[13px] text-slate-500">
                      {avatarUploading ? "正在上传..." : avatarFileName || (avatarDraft ? "已选择头像图片" : "未选择图片")}
                    </span>
                  </div>
                  {avatarDraft ? (
                    <button
                      type="button"
                      className="w-fit text-[13px] font-semibold text-slate-500 hover:text-slate-700"
                      onClick={() => {
                        setAvatarDraft("");
                        setAvatarFileName("");
                        setAvatarError(null);
                      }}
                    >
                      恢复姓名首字母头像
                    </button>
                  ) : null}
                </div>
              )}
              {avatarEditing ? (
                <p className="mt-1 text-[12px] text-slate-400">支持 JPG、PNG、WebP，选择后会上传本机图片。</p>
              ) : null}
              {avatarError ? <p className="mt-1 text-[12px] text-red-500">{avatarError}</p> : null}
            </div>
            <div className="flex shrink-0 items-center justify-end gap-3 sm:gap-2">
              {!avatarEditing ? (
                <button
                  type="button"
                  className="text-[13px] font-semibold text-blue-500 hover:text-blue-600"
                  onClick={() => {
                    setAvatarDraft(data.avatarUrl);
                    setAvatarFileName("");
                    setAvatarError(null);
                    setAvatarUploading(false);
                    setAvatarEditing(true);
                  }}
                >
                  修改
                </button>
              ) : (
                <>
                  <button
                    type="button"
                    className="rounded-[10px] bg-blue-600 px-3 py-1.5 text-[13px] font-semibold text-white hover:bg-blue-700"
                    onClick={submitAvatar}
                    disabled={avatarUploading}
                  >
                    保存
                  </button>
                  <button
                    type="button"
                    className="text-[13px] font-semibold text-slate-500 hover:text-slate-700"
                    onClick={() => {
                      setAvatarDraft(data.avatarUrl);
                      setAvatarFileName("");
                      setAvatarError(null);
                      setAvatarUploading(false);
                      setAvatarEditing(false);
                    }}
                  >
                    取消
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
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
          hint="如需修改工作邮箱，请联系管理员确认。"
          onSave={(v) => void commit({ email: v })}
        />
        <EditableTextRow label="手机号码" value={data.phone} onSave={(v) => void commit({ phone: v })} />
        <EditableTextRow label="分机" value={data.phoneExt} hint="内线号码。" onSave={(v) => void commit({ phoneExt: v })} />
        <EditableTextRow label="常驻办公地" value={data.location} onSave={(v) => void commit({ location: v })} />
        <EditableTextRow label="时区" value={data.timeZone} onSave={(v) => void commit({ timeZone: v })} />
      </SectionCard>

      <SectionCard title="组织信息" description="这些信息会用于团队协作、通知与权限识别。">
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
        <span>账号安全、登录方式与通知偏好可以在左侧对应页面管理。</span>
      </div>
    </>
  );
}
