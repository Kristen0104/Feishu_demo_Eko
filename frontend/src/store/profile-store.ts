import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { UserProfile } from "@/types/profile";

/** 通知设置（演示，可持久化到本地） */
export type NotificationSettings = {
  /** 会话与 @ 提醒 */
  sessionAndMention: boolean;
  /** 邮件摘要 */
  emailDigest: boolean;
  /** 日历与会议提醒 */
  calendarReminder: boolean;
  /** 登录与安全异常提醒 */
  securityAlert: boolean;
  /** 产品与功能更新（演示） */
  productUpdates: boolean;
};

export type SecurityPreferences = {
  /** 登录设备提醒 */
  loginDeviceAlert: boolean;
  /** 新设备登录需验证（演示开关） */
  newDeviceVerify: boolean;
};

type ProfileStoreState = {
  /** 覆盖默认 mock 的个人字段 */
  profileOverrides: Partial<UserProfile>;
  profileOwnerEmail: string | null;
  notificationSettings: NotificationSettings;
  securityPreferences: SecurityPreferences;
  /** 演示：上次保存时间文案 */
  lastSavedAt: string | null;
  setProfileOverrides: (patch: Partial<UserProfile>) => void;
  adoptProfileOwner: (email: string | null) => void;
  clearProfileState: () => void;
  setNotificationSettings: (patch: Partial<NotificationSettings>) => void;
  setSecurityPreferences: (patch: Partial<SecurityPreferences>) => void;
  markSaved: () => void;
  resetProfileOverrides: () => void;
};

const defaultNotifications: NotificationSettings = {
  sessionAndMention: true,
  emailDigest: true,
  calendarReminder: true,
  securityAlert: true,
  productUpdates: false,
};

const defaultSecurity: SecurityPreferences = {
  loginDeviceAlert: true,
  newDeviceVerify: false,
};

export const useProfileStore = create<ProfileStoreState>()(
  persist(
    (set) => ({
      profileOverrides: {},
      profileOwnerEmail: null,
      notificationSettings: defaultNotifications,
      securityPreferences: defaultSecurity,
      lastSavedAt: null,
      setProfileOverrides: (patch) =>
        set((state) => ({
          profileOverrides: { ...state.profileOverrides, ...patch },
        })),
      adoptProfileOwner: (email) =>
        set((state) => {
          const normalized = email?.trim().toLowerCase() || null;
          if (state.profileOwnerEmail === normalized) {
            return {};
          }
          return {
            profileOwnerEmail: normalized,
            profileOverrides: {},
            lastSavedAt: null,
          };
        }),
      clearProfileState: () =>
        set({
          profileOverrides: {},
          profileOwnerEmail: null,
          lastSavedAt: null,
        }),
      setNotificationSettings: (patch) =>
        set((state) => ({
          notificationSettings: { ...state.notificationSettings, ...patch },
        })),
      setSecurityPreferences: (patch) =>
        set((state) => ({
          securityPreferences: { ...state.securityPreferences, ...patch },
        })),
      markSaved: () =>
        set({
          lastSavedAt: new Date().toLocaleString("zh-CN", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          }),
        }),
      resetProfileOverrides: () => set({ profileOverrides: {}, lastSavedAt: null }),
    }),
    {
      name: "eko-profile-store",
      partialize: (s) => ({
        profileOverrides: s.profileOverrides,
        profileOwnerEmail: s.profileOwnerEmail,
        notificationSettings: s.notificationSettings,
        securityPreferences: s.securityPreferences,
        lastSavedAt: s.lastSavedAt,
      }),
    },
  ),
);
