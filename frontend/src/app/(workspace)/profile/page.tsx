import { ProfileOverview } from "@/components/profile/ProfileOverview";
import { getProfileData } from "@/lib/mock/profile-data";

export default function ProfileRoutePage() {
  return <ProfileOverview base={getProfileData()} />;
}
