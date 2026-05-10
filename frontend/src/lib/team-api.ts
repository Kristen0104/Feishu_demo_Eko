import { fetchEkoJson } from "@/lib/eko-api";
import type { TeamMember, TeamMemberDto } from "@/types/team";

function mapTeamMember(dto: TeamMemberDto): TeamMember {
  return {
    id: dto.id,
    email: dto.email,
    displayName: dto.display_name,
    role: dto.role,
    status: dto.status,
    avatarUrl: dto.avatar_url,
    isCurrentUser: dto.is_current_user,
    isRegisteredUser: dto.is_registered_user,
    invitedByName: dto.invited_by_name,
    createdAt: dto.created_at,
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

