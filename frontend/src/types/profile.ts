/** 个人资料（演示数据，后续可对接人事 / SSO） */

export type UserProfile = {
  displayName: string;
  nameEn: string;
  initials: string;
  email: string;
  phone: string;
  phoneExt: string;
  location: string;
  timeZone: string;
  employeeId: string;
  jobTitle: string;
  department: string;
  team: string;
  reportsTo: string;
  joinedAt: string;
  bio: string;
  languages: string[];
};
