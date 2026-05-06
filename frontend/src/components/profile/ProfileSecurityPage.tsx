"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { SectionCard } from "@/components/profile/profile-blocks";
import { fetchCurrentAuthUser, updateCurrentPassword, type AuthMeUser } from "@/lib/profile-api";
import { useProfileStore } from "@/store/profile-store";

const MOCK_DEVICES = [
  { id: "d1", label: "Chrome · macOS Sonoma", ip: "上海 · 电信", when: "今天 09:12", current: true },
  { id: "d2", label: "Safari · iPhone", ip: "上海 · 蜂窝网络", when: "昨天 18:40", current: false },
  { id: "d3", label: "Edge · Windows 11", ip: "新加坡", when: "2026-04-28", current: false },
];

export function ProfileSecurityPage() {
  const searchParams = useSearchParams();
  const securityPreferences = useProfileStore((s) => s.securityPreferences);
  const setSecurityPreferences = useProfileStore((s) => s.setSecurityPreferences);
  const markSaved = useProfileStore((s) => s.markSaved);
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
      markSaved();
      setOldPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (error) {
      setPwMsg(error instanceof Error ? error.message : "密码修改失败");
    }
  };

  return (
    <>
      <SectionCard title="登录方式" description="当前登录身份与飞书绑定状态来自后端账号服务。">
        <div className="space-y-3 py-4">
          {searchParams.get("feishu_bind") === "success" ? (
            <div className="rounded-[12px] border border-emerald-100 bg-emerald-50 px-3 py-2 text-[13px] font-medium text-emerald-700">
              飞书账号已绑定到当前网站账号。
            </div>
          ) : null}
          {searchParams.get("feishu_bind") === "error" ? (
            <div className="rounded-[12px] border border-rose-100 bg-rose-50 px-3 py-2 text-[13px] font-medium text-rose-700">
              飞书绑定失败，请确认当前已登录网站账号并重试。
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
              当前账号：{authUser?.display_name || "读取中"} {authUser?.email ? `· ${authUser.email}` : ""}
            </p>
            <p className="mt-1 text-[13px] text-slate-500">
              飞书 Open ID：{authUser?.feishu_user_id || "尚未绑定"}
            </p>
            {authError ? <p className="mt-2 text-[13px] text-rose-500">{authError}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/login/feishu/start?mode=bind"
              className="rounded-[12px] bg-blue-600 px-4 py-2.5 text-[13px] font-semibold text-white hover:bg-blue-700"
            >
              {authUser?.feishu_bound ? "重新绑定飞书" : "绑定飞书账号"}
            </Link>
            <span className="text-[13px] text-slate-500">
              绑定后，飞书登录和飞书消息事件会映射到同一个网站账号。
            </span>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="修改密码" description="修改当前网站账号密码；仅邮箱密码账号可使用。">
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

      <SectionCard title="安全偏好" description="开关只写入本地存储，不会改变真实账号安全策略。">
        <div className="py-2">
          <div className="flex flex-col gap-2 border-b border-slate-100 py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[15px] font-medium text-slate-900">新设备登录提醒</p>
              <p className="mt-1 text-[13px] text-slate-500">检测到陌生设备登录时推送通知（本地开关）。</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={securityPreferences.loginDeviceAlert}
              onClick={() => {
                setSecurityPreferences({
                  loginDeviceAlert: !securityPreferences.loginDeviceAlert,
                });
                markSaved();
              }}
              className={`relative h-8 w-[52px] shrink-0 rounded-full transition-colors ${
                securityPreferences.loginDeviceAlert ? "bg-blue-600" : "bg-slate-200"
              }`}
            >
              <span
                className={`absolute top-1 left-1 h-6 w-6 rounded-full bg-white shadow transition-transform ${
                  securityPreferences.loginDeviceAlert ? "translate-x-[22px]" : "translate-x-0"
                }`}
              />
            </button>
          </div>
          <div className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[15px] font-medium text-slate-900">新设备需二次验证</p>
              <p className="mt-1 text-[13px] text-slate-500">开启后陌生设备首次登录需 OTP（本地开关）。</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={securityPreferences.newDeviceVerify}
              onClick={() => {
                setSecurityPreferences({
                  newDeviceVerify: !securityPreferences.newDeviceVerify,
                });
                markSaved();
              }}
              className={`relative h-8 w-[52px] shrink-0 rounded-full transition-colors ${
                securityPreferences.newDeviceVerify ? "bg-blue-600" : "bg-slate-200"
              }`}
            >
              <span
                className={`absolute top-1 left-1 h-6 w-6 rounded-full bg-white shadow transition-transform ${
                  securityPreferences.newDeviceVerify ? "translate-x-[22px]" : "translate-x-0"
                }`}
              />
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="登录设备" description="以下为静态本地列表；下线按钮不会调用后端设备管理接口。">
        <div className="divide-y divide-slate-100">
          {MOCK_DEVICES.map((d) => (
            <div key={d.id} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="min-w-0">
                <p className="text-[15px] font-medium text-slate-900">
                  {d.label}
                  {d.current ? (
                    <span className="ml-2 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                      当前设备
                    </span>
                  ) : null}
                </p>
                <p className="mt-1 text-[13px] text-slate-500">
                  {d.ip} · {d.when}
                </p>
              </div>
              {!d.current ? (
                <button
                  type="button"
                  className="shrink-0 rounded-[10px] border border-slate-200 px-3 py-1.5 text-[13px] font-semibold text-slate-600 hover:bg-slate-50"
                  onClick={() => {
                    window.alert("演示：已请求下线该设备（未调用接口）");
                  }}
                >
                  下线
                </button>
              ) : (
                <span className="text-[12px] text-slate-400">—</span>
              )}
            </div>
          ))}
        </div>
      </SectionCard>
    </>
  );
}
