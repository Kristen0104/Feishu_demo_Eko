import { Suspense } from "react";

import { ProfileSecurityPage } from "@/components/profile/ProfileSecurityPage";

export default function ProfileSecurityRoutePage() {
  return (
    <Suspense fallback={null}>
      <ProfileSecurityPage />
    </Suspense>
  );
}
