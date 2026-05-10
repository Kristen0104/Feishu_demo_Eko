from __future__ import annotations

from fastapi import HTTPException

from app.core.security import AuthContext
from app.modules.auth.repository import AuthRepository
from app.modules.team.models import TeamMemberRole, TeamMemberStatus
from app.modules.team.repository import TeamRepository
from app.modules.team.schemas import TeamInviteRequest, TeamMemberSchema


class TeamService:
    def __init__(self, repository: TeamRepository, auth_repository: AuthRepository) -> None:
        self._repository = repository
        self._auth_repository = auth_repository

    async def list_members(self, auth_context: AuthContext) -> list[TeamMemberSchema]:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)
        members = await self._repository.list_members(team.id)
        return [await self._to_schema(member, auth_context) for member in members]

    async def invite_member(self, auth_context: AuthContext, payload: TeamInviteRequest) -> TeamMemberSchema:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)

        email = self._normalize_email(payload.email)
        inviter = await self._require_user(auth_context.user_id)
        target_user = await self._auth_repository.get_user_by_email(email)
        status = TeamMemberStatus.ACTIVE.value if target_user is not None else TeamMemberStatus.INVITED.value
        member = await self._repository.upsert_member(
            team_id=team.id,
            email=email,
            user_id=target_user.id if target_user is not None else None,
            display_name=target_user.display_name if target_user is not None else None,
            avatar_url=target_user.avatar_url if target_user is not None else None,
            role=TeamMemberRole.MEMBER.value,
            status=status,
            invited_by_user_id=inviter.id,
            invited_by_name=inviter.display_name,
        )
        return await self._to_schema(member, auth_context)

    async def remove_member(self, auth_context: AuthContext, member_id: str) -> None:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)

        member = await self._repository.get_member_by_id(team.id, member_id)
        if member is None:
            raise HTTPException(status_code=404, detail="Team member not found")
        if member.role == TeamMemberRole.OWNER.value:
            raise HTTPException(status_code=403, detail="Owner cannot be removed")
        await self._repository.delete_member(team.id, member_id)

    async def _ensure_owner_seeded(self, team_id: str, auth_context: AuthContext) -> None:
        if await self._repository.count_members(team_id) > 0:
            return

        user = await self._require_user(auth_context.user_id)
        email = self._normalize_email(user.email or "")
        await self._repository.upsert_member(
            team_id=team_id,
            email=email,
            user_id=user.id,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=TeamMemberRole.OWNER.value,
            status=TeamMemberStatus.ACTIVE.value,
            invited_by_user_id=None,
            invited_by_name=None,
        )

    async def _require_user(self, user_id: str):
        user = await self._auth_repository.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Authenticated user was not found")
        return user

    async def _to_schema(self, member, auth_context: AuthContext) -> TeamMemberSchema:
        return TeamMemberSchema(
            id=member.id,
            email=member.email,
            display_name=member.display_name,
            role=member.role,
            status=member.status,
            avatar_url=getattr(member, "avatar_url", None),
            is_current_user=member.user_id == auth_context.user_id,
            is_registered_user=member.user_id is not None,
            invited_by_name=getattr(member, "invited_by_name", None),
            created_at=member.created_at,
        )

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise HTTPException(status_code=400, detail="Invalid email")
        return normalized

