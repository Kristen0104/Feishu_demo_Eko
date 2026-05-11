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

export type SessionInviteStatus = "pending" | "accepted" | "declined" | "dismissed" | "expired";

export type SessionInviteDto = {
  id: string;
  session_id: string;
  session_title: string;
  inviter_user_id: string;
  inviter_name: string;
  invitee_user_id: string | null;
  invitee_email: string;
  invitee_name: string | null;
  status: SessionInviteStatus;
  is_expired: boolean;
  created_at: string;
  expires_at: string;
  responded_at: string | null;
};

export type SessionInvite = {
  id: string;
  sessionId: string;
  sessionTitle: string;
  inviterUserId: string;
  inviterName: string;
  inviteeUserId: string | null;
  inviteeEmail: string;
  inviteeName: string | null;
  status: SessionInviteStatus;
  isExpired: boolean;
  createdAt: string;
  expiresAt: string;
  respondedAt: string | null;
};
