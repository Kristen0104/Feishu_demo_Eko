from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.core.security import AuthContext
from app.modules.team.models import TeamMemberRole, TeamMemberStatus
from app.modules.team.schemas import TeamInviteRequest
from app.modules.team.service import TeamService


@dataclass
class _FakeUser:
    id: str
    email: str | None
    display_name: str
    avatar_url: str | None = None


@dataclass
class _FakeTeam:
    id: str
    name: str


@dataclass
class _FakeTeamMember:
    id: str
    team_id: str
    user_id: str | None
    email: str
    display_name: str | None
    avatar_url: str | None
    role: str
    status: str
    invited_by_user_id: str | None
    invited_by_name: str | None
    created_at: datetime
    updated_at: datetime


class _FakeTeamRepository:
    def __init__(self) -> None:
        self.team = _FakeTeam(id="team_default", name="Default Team")
        self.members: list[_FakeTeamMember] = []
        self._sequence = 0

    async def get_or_create_default_team(self) -> _FakeTeam:
        return self.team

    async def list_members(self, team_id: str) -> list[_FakeTeamMember]:
        assert team_id == self.team.id
        return list(
            sorted(
                self.members,
                key=lambda member: (
                    0 if member.role == TeamMemberRole.OWNER.value else 1,
                    0 if member.status == TeamMemberStatus.ACTIVE.value else 1,
                    (member.display_name or member.email).lower(),
                ),
            )
        )

    async def count_members(self, team_id: str) -> int:
        assert team_id == self.team.id
        return len(self.members)

    async def get_member_by_email(self, team_id: str, email: str) -> _FakeTeamMember | None:
        assert team_id == self.team.id
        for member in self.members:
            if member.email == email:
                return member
        return None

    async def get_member_by_id(self, team_id: str, member_id: str) -> _FakeTeamMember | None:
        assert team_id == self.team.id
        for member in self.members:
            if member.id == member_id:
                return member
        return None

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
    ) -> _FakeTeamMember:
        assert team_id == self.team.id
        member = await self.get_member_by_email(team_id, email)
        now = datetime.now(UTC)
        if member is None:
            self._sequence += 1
            member = _FakeTeamMember(
                id=f"tm_{self._sequence}",
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
            self.members.append(member)
            return member

        member.user_id = user_id or member.user_id
        member.display_name = display_name or member.display_name
        member.avatar_url = avatar_url or member.avatar_url
        member.role = role
        member.status = status
        member.invited_by_user_id = invited_by_user_id
        member.invited_by_name = invited_by_name
        member.updated_at = now
        return member

    async def delete_member(self, team_id: str, member_id: str) -> None:
        assert team_id == self.team.id
        self.members = [member for member in self.members if member.id != member_id]


class _FakeAuthRepository:
    def __init__(self, users: list[_FakeUser] | None = None) -> None:
        self.users = {user.id: user for user in users or []}
        self.users_by_email = {user.email: user for user in users or [] if user.email}

    async def get_user_by_id(self, user_id: str) -> _FakeUser | None:
        return self.users.get(user_id)

    async def get_user_by_email(self, email: str) -> _FakeUser | None:
        return self.users_by_email.get(email)


def test_empty_team_seeds_owner_from_current_user() -> None:
    async def run_test() -> None:
        owner = _FakeUser(id="user_owner", email="owner@example.com", display_name="Owner Name")
        service = TeamService(_FakeTeamRepository(), _FakeAuthRepository([owner]))

        members = await service.list_members(AuthContext(user_id=owner.id))

        assert len(members) == 1
        assert members[0].email == "owner@example.com"
        assert members[0].role == TeamMemberRole.OWNER.value
        assert members[0].status == TeamMemberStatus.ACTIVE.value
        assert members[0].is_current_user is True
        assert members[0].is_registered_user is True

    asyncio.run(run_test())


def test_inviting_existing_user_creates_active_member() -> None:
    async def run_test() -> None:
        owner = _FakeUser(id="user_owner", email="owner@example.com", display_name="Owner Name")
        teammate = _FakeUser(id="user_member", email="member@example.com", display_name="Member Name")
        service = TeamService(_FakeTeamRepository(), _FakeAuthRepository([owner, teammate]))

        member = await service.invite_member(AuthContext(user_id=owner.id), TeamInviteRequest(email=teammate.email))

        assert member.email == teammate.email
        assert member.role == TeamMemberRole.MEMBER.value
        assert member.status == TeamMemberStatus.ACTIVE.value
        assert member.display_name == "Member Name"
        assert member.is_registered_user is True
        assert member.invited_by_name == "Owner Name"

    asyncio.run(run_test())


def test_inviting_unknown_email_creates_pending_invite() -> None:
    async def run_test() -> None:
        owner = _FakeUser(id="user_owner", email="owner@example.com", display_name="Owner Name")
        service = TeamService(_FakeTeamRepository(), _FakeAuthRepository([owner]))

        member = await service.invite_member(
            AuthContext(user_id=owner.id),
            TeamInviteRequest(email="invitee@example.com"),
        )

        assert member.email == "invitee@example.com"
        assert member.status == TeamMemberStatus.INVITED.value
        assert member.display_name is None
        assert member.is_registered_user is False
        assert member.invited_by_name == "Owner Name"

    asyncio.run(run_test())


def test_reinviting_same_email_updates_existing_row() -> None:
    async def run_test() -> None:
        owner = _FakeUser(id="user_owner", email="owner@example.com", display_name="Owner Name")
        teammate = _FakeUser(id="user_member", email="member@example.com", display_name="Member Name")
        repository = _FakeTeamRepository()
        auth_repository = _FakeAuthRepository([owner, teammate])
        service = TeamService(repository, auth_repository)

        first_invite = await service.invite_member(AuthContext(user_id=owner.id), TeamInviteRequest(email=teammate.email))
        second_invite = await service.invite_member(AuthContext(user_id=owner.id), TeamInviteRequest(email=teammate.email))

        assert first_invite.id == second_invite.id
        assert len(repository.members) == 2
        assert second_invite.status == TeamMemberStatus.ACTIVE.value

    asyncio.run(run_test())


def test_owner_cannot_be_removed() -> None:
    async def run_test() -> None:
        owner = _FakeUser(id="user_owner", email="owner@example.com", display_name="Owner Name")
        repository = _FakeTeamRepository()
        service = TeamService(repository, _FakeAuthRepository([owner]))

        members = await service.list_members(AuthContext(user_id=owner.id))

        with pytest.raises(HTTPException, match="Owner cannot be removed"):
            await service.remove_member(AuthContext(user_id=owner.id), members[0].id)

    asyncio.run(run_test())
