export type TeamMemberRole = "owner" | "member";
export type TeamMemberStatus = "active" | "invited";

export type TeamMemberDto = {
  id: string;
  email: string;
  display_name: string | null;
  role: TeamMemberRole;
  status: TeamMemberStatus;
  avatar_url: string | null;
  is_current_user: boolean;
  is_registered_user: boolean;
  invited_by_name: string | null;
  created_at: string;
};

export type TeamMember = {
  id: string;
  email: string;
  displayName: string | null;
  role: TeamMemberRole;
  status: TeamMemberStatus;
  avatarUrl: string | null;
  isCurrentUser: boolean;
  isRegisteredUser: boolean;
  invitedByName: string | null;
  createdAt: string;
};

