"use client";

import { useState } from "react";

import { SectionCard } from "@/components/profile/profile-blocks";
import { useProfileStore } from "@/store/profile-store";

const MOCK_DEVICES = [
  { id: "d1", label: "Chrome · macOS Sonoma", ip: "上海 · 电信", when: "今天 09:12", current: true },
  { id: "d2", label: "Safari · iPhone", ip: "上海 · 蜂窝网络", when: "昨天 18:40", current: false },
  { id: "d3", label: "Edge · Windows 11", ip: "新加坡", when: "2026-04-28", current: false },
];

export function ProfileSecurityPage() {
  const securityPreferences = useProfileStore((s) => s.securityPreferences);
  const setSecurityPreferences = useProfileStore((s) => s.setSecurityPreferences);
  const markSaved = useProfileStore((s) => s.markSaved);

  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwMsg, setPwMsg] = useState<string | null>(null);

  const submitPasswordDemo = () => {
    if (!oldPw || !newPw || !confirmPw) {
      setPwMsg("请填写全部字段（演示）");
      return;
    }
    if (newPw !== confirmPw) {
      setPwMsg("两次新密码不一致");
      return;
    }
    setPwMsg("已保存到本地演示状态（未调用后端 API）");
    markSaved();
    setOldPw("");
    setNewPw("");
    setConfirmPw("");
  };

  return (
    <>
      <SectionCard title="登录方式" description="当前登录身份由后端鉴权提供；绑定状态与 MFA 仍未接真实账号安全服务。">
        <div className="space-y-3 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[13px] font-medium text-slate-700">
              企业邮箱 + SSO
            </span>
            <span className="text-[13px] text-slate-500">与飞书扫码 / MFA 可在网关层对接。</span>
          </div>
          <p className="text-[13px] leading-relaxed text-slate-500">
            当前会话：浏览器保存后端访问令牌；本页安全设置仍为本地演示偏好。
          </p>
        </div>
      </SectionCard>

      <SectionCard title="修改密码" description="本区域仅做前端表单校验，不调用后端改密 API。">
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
              onClick={submitPasswordDemo}
            >
              保存新密码（本地演示）
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
