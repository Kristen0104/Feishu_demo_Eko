"use client";

import { SectionCard, ToggleRow } from "@/components/profile/profile-blocks";
import { useProfileStore } from "@/store/profile-store";

export function ProfileNotificationsPage() {
  const notificationSettings = useProfileStore((s) => s.notificationSettings);
  const setNotificationSettings = useProfileStore((s) => s.setNotificationSettings);
  const markSaved = useProfileStore((s) => s.markSaved);

  const patch = (partial: Parameters<typeof setNotificationSettings>[0]) => {
    setNotificationSettings(partial);
    markSaved();
  };

  return (
    <>
      <SectionCard title="消息与协作" description="控制即时消息类通知的本地演示开关；暂不回写后端通知服务。">
        <ToggleRow
          label="会话与 @ 提醒"
          description="群聊、私聊中被 @ 或指派任务时通知。"
          checked={notificationSettings.sessionAndMention}
          onChange={(v) => patch({ sessionAndMention: v })}
        />
        <ToggleRow
          label="邮件摘要"
          description="每日一次未读摘要发到工作邮箱（本地演示）。"
          checked={notificationSettings.emailDigest}
          onChange={(v) => patch({ emailDigest: v })}
        />
      </SectionCard>

      <SectionCard title="日历与安全" description="日程类与安全类提醒通道；当前只保存在本机。">
        <ToggleRow
          label="日历与会议提醒"
          description="会议开始前推送。"
          checked={notificationSettings.calendarReminder}
          onChange={(v) => patch({ calendarReminder: v })}
        />
        <ToggleRow
          label="登录与安全异常"
          description="异地登录、密码变更等安全事件。"
          checked={notificationSettings.securityAlert}
          onChange={(v) => patch({ securityAlert: v })}
        />
      </SectionCard>

      <SectionCard title="产品动态" description="可选接收产品更新与调研邀请（本地演示）。">
        <ToggleRow
          label="产品与功能更新"
          checked={notificationSettings.productUpdates}
          onChange={(v) => patch({ productUpdates: v })}
        />
      </SectionCard>
    </>
  );
}
