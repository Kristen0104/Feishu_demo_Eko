"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { AnimatePresence, motion } from "@/components/MotionShim";
import { useAppStore } from "@/store/app-store";

const nav = [
  { href: "/profile", label: "我的资料", icon: UserIcon },
  { href: "/profile/security", label: "账号与安全", icon: ShieldIcon },
  { href: "/profile/notifications", label: "通知设置", icon: BellIcon },
] as const;

function UserIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="7" r="3.2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5 16.5C5.6 13.8 7.5 12.2 10 12.2s4.4 1.6 5 4.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M10 3 4 5.5v5.4c0 3.8 2.5 7.2 6 8.6 3.5-1.4 6-4.8 6-8.6V5.5L10 3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M10 4a3 3 0 0 0-3 3v2.2l-.9 2.6h9.8l-.9-2.6V7a3 3 0 0 0-3-3Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M8 15.5h4a2 2 0 0 1-4 0Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

export function ProfileShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useAppStore((s) => s.logout);

  function handleLogout() {
    logout();
    router.push("/login");
    router.refresh();
  }

  return (
    <main className="min-h-full bg-[radial-gradient(circle_at_top,#EDF4FF_0%,#F5F8FD_45%,#EEF3FF_100%)] px-3 pb-24 pt-4 text-slate-900 sm:px-5 sm:pb-16 sm:pt-6">
      <div className="mx-auto max-w-[1040px]">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 sm:mb-8 sm:gap-4">
          <div className="flex flex-wrap items-center gap-3 text-[13px] text-slate-500">
            <Link
              href="/sessions"
              prefetch={false}
              className="inline-flex items-center gap-1.5 rounded-[12px] border border-slate-200 bg-white px-3 py-2 font-medium text-slate-600 shadow-[0_4px_12px_rgba(15,23,42,0.04)] transition hover:bg-slate-50"
            >
              <span className="text-[15px] leading-none">←</span>
              返回会话
            </Link>
            <span className="hidden text-slate-300 sm:inline">/</span>
            <span className="hidden font-semibold text-slate-800 sm:inline">个人资料</span>
          </div>
          <div className="flex min-w-0 flex-wrap items-center gap-2 text-[12px] text-slate-400">
            <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-700">在线</span>
            <span className="min-w-0">个人资料已启用同步</span>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-8">
          <aside className="space-y-2 lg:sticky lg:top-6 lg:self-start">
            <nav className="flex gap-2 overflow-x-auto rounded-[20px] border border-white/80 bg-white/90 p-2 shadow-[0_12px_36px_rgba(15,23,42,0.05)] backdrop-blur-sm lg:block lg:overflow-visible">
              {nav.map((item) => {
                const active = pathname === item.href;
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    prefetch={false}
                    className={`flex shrink-0 items-center gap-2 rounded-[14px] px-3 py-2.5 text-left text-[13px] font-medium transition lg:mt-1 lg:w-full lg:gap-3 lg:px-4 lg:py-3 lg:text-[14px] lg:first:mt-0 ${
                      active
                        ? "bg-blue-50 font-semibold text-blue-600 shadow-[inset_3px_0_0_#2563EB]"
                        : "text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <Icon />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </aside>

          <div className="min-w-0 space-y-8">
            <AnimatePresence mode="wait">
              <motion.div
                key={pathname}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
                className="space-y-6"
              >
                {children}
              </motion.div>
            </AnimatePresence>

            <section className="border-t border-slate-200/90 pt-8">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full rounded-[14px] border border-rose-200/90 bg-rose-50/80 px-4 py-3 text-center text-[14px] font-semibold text-rose-700 shadow-[0_4px_14px_rgba(225,29,72,0.08)] transition hover:bg-rose-100/90 sm:w-auto sm:min-w-[200px]"
              >
                退出登录
              </button>
              <p className="mt-2 text-[12px] text-slate-400">退出后将清除本会话的登录状态并返回登录页。</p>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
