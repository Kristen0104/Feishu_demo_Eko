"use client";

import { useEffect, useRef } from "react";

import { apiUrl } from "@/lib/eko-api";
import { clearAccessToken, readAccessToken } from "@/lib/auth-token";
import { readAuth } from "@/lib/auth-session";
import { useAppStore } from "@/store/app-store";
import { useProfileStore } from "@/store/profile-store";

/** 在 Zustand persist 完成后再对齐浏览器中的登录票据（15 天 localStorage / 单次会话 sessionStorage） */
export function AuthBootstrap() {
  const ran = useRef(false);

  useEffect(() => {
    const syncAuth = () => {
      if (ran.current) return;
      ran.current = true;
      try {
        const auth = readAuth();
        if (auth) {
          useAppStore.getState().setLogin(auth.email, { fromStorage: true });
        } else if (useAppStore.getState().isLoggedIn) {
          useAppStore.getState().logout();
        }

        queueMicrotask(() => {
          const token = readAccessToken();
          if (!token) return;
          void fetch(apiUrl("/api/v1/auth/me"), { headers: { Authorization: `Bearer ${token}` } })
            .then((res) => {
              if (res.status === 401) {
                clearAccessToken();
                useProfileStore.getState().clearProfileState();
                useAppStore.getState().logout();
              }
            })
            .catch(() => {
              /* 离线或后端未起：保留本地会话 */
            });
        });
      } catch {
        ran.current = false;
      }
    };

    if (useAppStore.persist.hasHydrated()) {
      syncAuth();
      return;
    }

    const unsub = useAppStore.persist.onFinishHydration(() => {
      syncAuth();
    });

    /** persist 回调偶发不触发（存储异常 / 严格模式）时仍同步登录票据，避免页面逻辑长时间不一致 */
    const timer = window.setTimeout(() => {
      if (!ran.current) {
        syncAuth();
      }
    }, 800);

    return () => {
      window.clearTimeout(timer);
      try {
        unsub?.();
      } catch {
        /* ignore */
      }
    };
  }, []);

  return null;
}
