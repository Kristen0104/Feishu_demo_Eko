import { deriveInitials } from "@/lib/profile-merge";
import type { UserProfile } from "@/types/profile";

export function getDefaultProfile(): UserProfile {
  const displayName = "";
  const nameEn = "";
  return {
    displayName,
    nameEn,
    initials: deriveInitials(displayName, nameEn),
    email: "",
    phone: "",
    phoneExt: "",
    location: "",
    timeZone: "",
    employeeId: "",
    jobTitle: "",
    department: "",
    team: "",
    reportsTo: "",
    joinedAt: "",
    bio: "",
    languages: [],
  };
}
