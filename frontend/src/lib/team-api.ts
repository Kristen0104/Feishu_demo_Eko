import { fetchEkoJson } from "@/lib/eko-api";
import { resolveAvatarUrl } from "@/lib/profile-api";
import { looksLikeTechnicalSessionTitle } from "@/lib/session-title";
import type { SessionInvite, SessionInviteDto, SessionInviteStatus, TeamMember, TeamMemberDto } from "@/types/team";

function mapTeamMember(dto: TeamMemberDto): TeamMember {
  return {
    id: dto.id,
    email: dto.email,
    displayName: dto.display_name,
    role: dto.role,
    status: dto.status,
    avatarUrl: resolveAvatarUrl(dto.avatar_url),
    isCurrentUser: dto.is_current_user,
    isRegisteredUser: dto.is_registered_user,
    invitedByName: dto.invited_by_name,
    createdAt: dto.created_at,
  };
}

function mapSessionInvite(dto: SessionInviteDto): SessionInvite {
  const sessionTitle = dto.session_title?.trim() || "";
  return {
    id: dto.id,
    sessionId: dto.session_id,
    sessionTitle: sessionTitle && !looksLikeTechnicalSessionTitle(sessionTitle) ? sessionTitle : "会话邀请",
    inviterUserId: dto.inviter_user_id,
    inviterName: dto.inviter_name,
    inviteeUserId: dto.invitee_user_id,
    inviteeEmail: dto.invitee_email,
    inviteeName: dto.invitee_name,
    status: dto.status,
    isExpired: dto.is_expired,
    createdAt: dto.created_at,
    expiresAt: dto.expires_at,
    respondedAt: dto.responded_at,
  };
}

export async function fetchTeamMembers(): Promise<TeamMember[]> {
  const data = await fetchEkoJson<TeamMemberDto[]>("/api/v1/team/members");
  return data.map(mapTeamMember);
}

export async function inviteTeamMember(email: string): Promise<TeamMember> {
  const data = await fetchEkoJson<TeamMemberDto>("/api/v1/team/members/invite", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  return mapTeamMember(data);
}

export async function removeTeamMember(memberId: string): Promise<void> {
  await fetchEkoJson<null>(`/api/v1/team/members/${memberId}`, {
    method: "DELETE",
  });
}

export async function createSessionInvite(sessionId: string, input: { memberId?: string; email?: string }): Promise<SessionInvite> {
  const data = await fetchEkoJson<SessionInviteDto>(`/api/v1/team/sessions/${encodeURIComponent(sessionId)}/invites`, {
    method: "POST",
    body: JSON.stringify({ member_id: input.memberId, email: input.email }),
  });
  return mapSessionInvite(data);
}

export async function fetchSessionInvites(sessionId: string): Promise<SessionInvite[]> {
  const data = await fetchEkoJson<SessionInviteDto[]>(`/api/v1/team/sessions/${encodeURIComponent(sessionId)}/invites`);
  return data.map(mapSessionInvite);
}

export async function fetchMySessionInvites(): Promise<SessionInvite[]> {
  const data = await fetchEkoJson<SessionInviteDto[]>("/api/v1/team/session-invites");
  return data.map(mapSessionInvite);
}

export async function updateSessionInvite(inviteId: string, action: Extract<SessionInviteStatus, "accepted" | "declined" | "dismissed">): Promise<SessionInvite> {
  const data = await fetchEkoJson<SessionInviteDto>(`/api/v1/team/session-invites/${encodeURIComponent(inviteId)}`, {
    method: "PATCH",
    body: JSON.stringify({ action }),
  });
  return mapSessionInvite(data);
}
