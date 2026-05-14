"use client";

import { SectionCard } from "@/components/profile/profile-blocks";

export function ProfileNotificationsPage() {
  return (
    <SectionCard title="通知设置" description="当前通知偏好由组织统一管理。">
      <div className="py-6 text-[14px] leading-6 text-slate-500">
        会话提醒、协作通知与系统消息会按团队策略发送。如需调整接收范围，请联系管理员处理。
      </div>
    </SectionCard>
  );
}
