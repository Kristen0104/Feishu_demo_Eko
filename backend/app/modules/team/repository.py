from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.team.models import SessionCollaborationInvite, Team, TeamMember, TeamMemberRole, TeamMemberStatus


DEFAULT_TEAM_ID = "team_default"


class TeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create_default_team(self) -> Team:
        team = await self._session.scalar(select(Team).where(Team.id == DEFAULT_TEAM_ID))
        if team is not None:
            return team

        now = datetime.now(UTC)
        team = Team(id=DEFAULT_TEAM_ID, name="默认团队", created_at=now, updated_at=now)
        self._session.add(team)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._session.scalar(select(Team).where(Team.id == DEFAULT_TEAM_ID))
            if existing is not None:
                return existing
            raise
        await self._commit()
        return team

    async def list_members(self, team_id: str) -> list[TeamMember]:
        members = list(
            await self._session.scalars(
                select(TeamMember).where(TeamMember.team_id == team_id)
            )
        )
        return sorted(
            members,
            key=lambda member: (
                0 if member.role == TeamMemberRole.OWNER.value else 1,
                0 if member.status == TeamMemberStatus.ACTIVE.value else 1,
                (member.display_name or member.email).lower(),
            ),
        )

    async def count_members(self, team_id: str) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).select_from(TeamMember).where(TeamMember.team_id == team_id)
            )
            or 0
        )

    async def get_member_by_email(self, team_id: str, email: str) -> TeamMember | None:
        return await self._session.scalar(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.email == email)
        )

    async def get_member_by_id(self, team_id: str, member_id: str) -> TeamMember | None:
        return await self._session.scalar(
            select(TeamMember).where(TeamMember.team_id == team_id, TeamMember.id == member_id)
        )

    async def upsert_member(
        self,
        *,
        team_id: str,
        email: str,
        user_id: str | None,
        display_name: str | None,
        avatar_url: str | None,
        role: str,
        status: str,
        invited_by_user_id: str | None,
        invited_by_name: str | None,
    ) -> TeamMember:
        now = datetime.now(UTC)
        member = await self.get_member_by_email(team_id, email)
        if member is None:
            member = TeamMember(
                team_id=team_id,
                user_id=user_id,
                email=email,
                display_name=display_name,
                avatar_url=avatar_url,
                role=role,
                status=status,
                invited_by_user_id=invited_by_user_id,
                invited_by_name=invited_by_name,
                created_at=now,
                updated_at=now,
            )
            self._session.add(member)
        else:
            if member.role != TeamMemberRole.OWNER.value:
                member.role = role
            member.user_id = user_id or member.user_id
            member.display_name = display_name or member.display_name
            member.avatar_url = avatar_url or member.avatar_url
            member.status = status
            member.invited_by_user_id = invited_by_user_id
            member.invited_by_name = invited_by_name
            member.updated_at = now

        await self._session.flush()
        await self._commit()
        return member

    async def delete_member(self, team_id: str, member_id: str) -> None:
        member = await self.get_member_by_id(team_id, member_id)
        if member is None:
            return
        await self._session.delete(member)
        await self._commit()

    async def create_session_invite(
        self,
        *,
        team_id: str,
        session_id: str,
        session_title: str,
        inviter_user_id: str,
        inviter_name: str,
        invitee_user_id: str | None,
        invitee_email: str,
        invitee_name: str | None,
        expires_at: datetime,
    ) -> SessionCollaborationInvite:
        now = datetime.now(UTC)
        existing = await self._session.scalar(
            select(SessionCollaborationInvite).where(
                SessionCollaborationInvite.team_id == team_id,
                SessionCollaborationInvite.session_id == session_id,
                SessionCollaborationInvite.invitee_email == invitee_email,
                SessionCollaborationInvite.status == "pending",
            )
        )
        if existing is not None:
            existing.session_title = session_title
            existing.inviter_user_id = inviter_user_id
            existing.inviter_name = inviter_name
            existing.invitee_user_id = invitee_user_id or existing.invitee_user_id
            existing.invitee_name = invitee_name or existing.invitee_name
            existing.created_at = now
            existing.expires_at = expires_at
            await self._session.flush()
            await self._commit()
            return existing

        invite = SessionCollaborationInvite(
            team_id=team_id,
            session_id=session_id,
            session_title=session_title,
            inviter_user_id=inviter_user_id,
            inviter_name=inviter_name,
            invitee_user_id=invitee_user_id,
            invitee_email=invitee_email,
            invitee_name=invitee_name,
            status="pending",
            created_at=now,
            expires_at=expires_at,
        )
        self._session.add(invite)
        await self._session.flush()
        await self._commit()
        return invite

    async def list_session_invites(self, team_id: str, session_id: str) -> list[SessionCollaborationInvite]:
        invites = list(
            await self._session.scalars(
                select(SessionCollaborationInvite).where(
                    SessionCollaborationInvite.team_id == team_id,
                    SessionCollaborationInvite.session_id == session_id,
                )
            )
        )
        return sorted(invites, key=lambda invite: invite.created_at, reverse=True)

    async def list_invites_for_user(self, *, team_id: str, user_id: str, email: str | None) -> list[SessionCollaborationInvite]:
        conditions = [SessionCollaborationInvite.invitee_user_id == user_id]
        if email:
            conditions.append(SessionCollaborationInvite.invitee_email == email)
        invites = list(
            await self._session.scalars(
                select(SessionCollaborationInvite).where(
                    SessionCollaborationInvite.team_id == team_id,
                    or_(*conditions),
                )
            )
        )
        return sorted(invites, key=lambda invite: invite.created_at, reverse=True)

    async def get_session_invite_by_id(self, team_id: str, invite_id: str) -> SessionCollaborationInvite | None:
        return await self._session.scalar(
            select(SessionCollaborationInvite).where(
                SessionCollaborationInvite.team_id == team_id,
                SessionCollaborationInvite.id == invite_id,
            )
        )

    async def update_session_invite_status(self, invite: SessionCollaborationInvite, status: str) -> SessionCollaborationInvite:
        invite.status = status
        invite.responded_at = datetime.now(UTC)
        await self._session.flush()
        await self._commit()
        return invite

    async def _commit(self) -> None:
        commit = getattr(self._session, "commit", None)
        if commit is None:
            return
        await commit()
