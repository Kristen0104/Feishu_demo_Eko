from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException

from app.core.security import AuthContext
from app.modules.auth.repository import AuthRepository
from app.modules.sync.service import SyncService
from app.modules.team.models import TeamMemberRole, TeamMemberStatus
from app.modules.team.repository import TeamRepository
from app.modules.team.schemas import (
    SessionCollaborationInviteSchema,
    SessionInviteActionRequest,
    SessionInviteRequest,
    TeamInviteRequest,
    TeamMemberSchema,
)


class TeamService:
    def __init__(self, repository: TeamRepository, auth_repository: AuthRepository, sync_service: SyncService) -> None:
        self._repository = repository
        self._auth_repository = auth_repository
        self._sync_service = sync_service

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

    async def create_session_invite(
        self,
        auth_context: AuthContext,
        session_id: str,
        payload: SessionInviteRequest,
    ) -> SessionCollaborationInviteSchema:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)
        inviter = await self._require_user(auth_context.user_id)
        target_member = None
        if payload.member_id:
            target_member = await self._repository.get_member_by_id(team.id, payload.member_id)
            if target_member is None:
                raise HTTPException(status_code=404, detail="Team member not found")
        email = self._normalize_email(payload.email or target_member.email if target_member is not None else payload.email or "")
        if not email:
            raise HTTPException(status_code=400, detail="Invitee email is required")
        if inviter.email and self._normalize_email(inviter.email) == email:
            raise HTTPException(status_code=400, detail="Cannot invite yourself")

        target_user = await self._auth_repository.get_user_by_email(email)
        session = await self._sync_service.get_session(session_id, user_id=auth_context.user_id)
        if session is None:
            session = await self._sync_service.get_session(session_id)
        session_title = session.title if session is not None else session_id
        invitee_name = (
            target_member.display_name
            if target_member is not None and target_member.display_name
            else target_user.display_name
            if target_user is not None
            else None
        )
        invite = await self._repository.create_session_invite(
            team_id=team.id,
            session_id=session_id,
            session_title=session_title,
            inviter_user_id=inviter.id,
            inviter_name=inviter.display_name,
            invitee_user_id=target_user.id if target_user is not None else target_member.user_id if target_member is not None else None,
            invitee_email=email,
            invitee_name=invitee_name,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        await self._sync_service.add_session_participant(session_id, invitee_user_id=invite.invitee_user_id, invitee_email=email)
        await self._publish_session_invite(invite)
        return self._invite_to_schema(invite)

    async def list_session_invites(self, auth_context: AuthContext, session_id: str) -> list[SessionCollaborationInviteSchema]:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)
        invites = await self._repository.list_session_invites(team.id, session_id)
        return [self._invite_to_schema(invite) for invite in invites]

    async def list_my_session_invites(self, auth_context: AuthContext) -> list[SessionCollaborationInviteSchema]:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)
        user = await self._require_user(auth_context.user_id)
        email = self._normalize_email(user.email or "") if user.email else None
        invites = await self._repository.list_invites_for_user(team_id=team.id, user_id=user.id, email=email)
        return [self._invite_to_schema(invite) for invite in invites]

    async def update_session_invite(
        self,
        auth_context: AuthContext,
        invite_id: str,
        payload: SessionInviteActionRequest,
    ) -> SessionCollaborationInviteSchema:
        team = await self._repository.get_or_create_default_team()
        await self._ensure_owner_seeded(team.id, auth_context)
        user = await self._require_user(auth_context.user_id)
        invite = await self._repository.get_session_invite_by_id(team.id, invite_id)
        if invite is None:
            raise HTTPException(status_code=404, detail="Session invite not found")
        normalized_email = self._normalize_email(user.email or "") if user.email else None
        if invite.invitee_user_id != user.id and invite.invitee_email != normalized_email:
            raise HTTPException(status_code=403, detail="This invite belongs to another user")
        status = "expired" if self._is_expired(invite) else payload.action
        invite = await self._repository.update_session_invite_status(invite, status)
        if status == "accepted":
            await self._sync_service.add_session_participant(
                invite.session_id,
                invitee_user_id=user.id,
                invitee_email=invite.invitee_email,
            )
        return self._invite_to_schema(invite)

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

    async def _publish_session_invite(self, invite) -> None:
        await self._sync_service.emit(
            f"user:{invite.invitee_user_id}" if invite.invitee_user_id else f"email:{invite.invitee_email}",
            {
                "type": "SESSION_INVITE_CREATED",
                "session_id": invite.session_id,
                "payload": self._invite_to_schema(invite).model_dump(mode="json"),
            },
        )

    def _invite_to_schema(self, invite) -> SessionCollaborationInviteSchema:
        return SessionCollaborationInviteSchema(
            id=invite.id,
            session_id=invite.session_id,
            session_title=invite.session_title,
            inviter_user_id=invite.inviter_user_id,
            inviter_name=invite.inviter_name,
            invitee_user_id=invite.invitee_user_id,
            invitee_email=invite.invitee_email,
            invitee_name=invite.invitee_name,
            status="expired" if self._is_expired(invite) and invite.status == "pending" else invite.status,
            is_expired=self._is_expired(invite),
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            responded_at=invite.responded_at,
        )

    def _is_expired(self, invite) -> bool:
        expires_at = invite.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC)
