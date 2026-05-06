import type { UserProfile } from "@/types/profile";

const demoProfile: UserProfile = {
  displayName: "Sarah Chen",
  nameEn: "Sarah Chen",
  initials: "SC",
  email: "sarah.chen@eko.ai",
  phone: "+86 138 **** 6820",
  phoneExt: "8092",
  location: "中国 · 上海 · 徐汇区",
  timeZone: "(GMT+08:00) 北京、重庆、香港、乌鲁木齐",
  employeeId: "FS-10842",
  jobTitle: "高级产品运营",
  department: "市场部",
  team: "飞书市场部 · 增长组",
  reportsTo: "Michael Zhang（产品运营负责人）",
  joinedAt: "2022-03-15",
  bio: "负责市场增长与会话类 AI 工作空间的试点落地，协同销售与解决方案团队推进客户成功。",
  languages: ["中文（简体）", "English"],
};

export function getProfileData(): UserProfile {
  return demoProfile;
}
