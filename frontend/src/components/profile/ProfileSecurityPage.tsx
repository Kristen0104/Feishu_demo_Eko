"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { SectionCard } from "@/components/profile/profile-blocks";
import {
  fetchCurrentAuthUser,
  updateCurrentPassword,
  type AuthMeUser,
} from "@/lib/profile-api";

export function ProfileSecurityPage() {
  const searchParams = useSearchParams();
  const [authUser, setAuthUser] = useState<AuthMeUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwMsg, setPwMsg] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchCurrentAuthUser()
      .then((user) => {
        if (!alive) return;
        setAuthUser(user);
        setAuthError(null);
      })
      .catch((error) => {
        if (!alive) return;
        setAuthError(error instanceof Error ? error.message : "读取账号状态失败");
      });
    return () => {
      alive = false;
    };
  }, []);

  const accountLabel = authUser?.display_name || authUser?.email || "读取中";
  const accountDetail = authUser?.email && authUser.email !== accountLabel ? authUser.email : null;

  const submitPassword = async () => {
    if (!oldPw || !newPw || !confirmPw) {
      setPwMsg("请填写全部字段");
      return;
    }
    if (newPw !== confirmPw) {
      setPwMsg("两次新密码不一致");
      return;
    }
    try {
      await updateCurrentPassword(oldPw, newPw);
      setPwMsg("密码已更新");
      setOldPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (error) {
      setPwMsg(error instanceof Error ? error.message : "密码修改失败");
    }
  };

  return (
    <>
      <SectionCard title="登录方式" description="管理当前账号可以使用的登录方式。">
        <div className="space-y-3 py-4">
          {searchParams.get("feishu_bind") === "success" ? (
            <div className="rounded-[12px] border border-emerald-100 bg-emerald-50 px-3 py-2 text-[13px] font-medium text-emerald-700">
              飞书账号已绑定。
            </div>
          ) : null}
          {searchParams.get("feishu_bind") === "error" ? (
            <div className="rounded-[12px] border border-rose-100 bg-rose-50 px-3 py-2 text-[13px] font-medium text-rose-700">
              飞书绑定失败，请确认当前已登录并重试。
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[13px] font-medium text-slate-700">
              邮箱密码
            </span>
            <span
              className={`rounded-full px-3 py-1 text-[13px] font-medium ${
                authUser?.feishu_bound
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-amber-50 text-amber-700"
              }`}
            >
              {authUser?.feishu_bound ? "已绑定飞书" : "未绑定飞书"}
            </span>
          </div>
          <div className="rounded-[14px] border border-slate-100 bg-slate-50/70 px-4 py-3">
            <p className="text-[13px] font-medium text-slate-700">
              当前账号：{accountLabel}
            </p>
            {accountDetail ? <p className="mt-1 text-[13px] text-slate-500">{accountDetail}</p> : null}
            <p className="mt-1 text-[13px] text-slate-500">
              飞书账号：{authUser?.feishu_bound ? "已绑定" : "待绑定"}
            </p>
            {authError ? <p className="mt-2 text-[13px] text-rose-500">账号状态读取失败，请刷新后重试。</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/login/feishu/start?mode=bind"
              className="rounded-[12px] bg-blue-600 px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-blue-700"
            >
              {authUser?.feishu_bound ? "重新绑定飞书" : "绑定飞书账号"}
            </Link>
            <span className="text-[13px] text-slate-500">
              绑定后可使用同一个账号登录，并接收飞书内的协作消息。
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="修改密码" description="用于邮箱密码登录的账号安全校验。">
        <div className="grid gap-4 py-4 sm:max-w-md">
          <label className="block text-[13px] font-medium text-slate-600">
            当前密码
            <input
              type="password"
              autoComplete="current-password"
              className="mt-1 w-full rounded-[12px] border border-slate-200 px-3 py-2 text-[15px] outline-none ring-blue-500/30 focus:ring-2"
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
            />
          </label>
          <label className="block text-[13px] font-medium text-slate-600">
            新密码
            <input
              type="password"
              autoComplete="new-password"
              className="mt-1 w-full rounded-[12px] border border-slate-200 px-3 py-2 text-[15px] outline-none ring-blue-500/30 focus:ring-2"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
            />
          </label>
          <label className="block text-[13px] font-medium text-slate-600">
            确认新密码
            <input
              type="password"
              autoComplete="new-password"
              className="mt-1 w-full rounded-[12px] border border-slate-200 px-3 py-2 text-[15px] outline-none ring-blue-500/30 focus:ring-2"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-[12px] bg-blue-600 px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-blue-700"
              onClick={() => void submitPassword()}
            >
              保存新密码
            </button>
            {pwMsg ? <span className="text-[13px] text-emerald-600">{pwMsg}</span> : null}
          </div>
        </div>
      </SectionCard>
    </>
  );
}
