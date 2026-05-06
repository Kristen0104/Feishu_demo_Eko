import { ProfileOverview } from "@/components/profile/ProfileOverview";
import { getDefaultProfile } from "@/lib/default-profile";

export default function ProfileRoutePage() {
  return <ProfileOverview base={getDefaultProfile()} />;
}
