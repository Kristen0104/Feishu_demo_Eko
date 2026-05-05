from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security import AuthContext
from app.modules.team.dependencies import get_team_service
from app.modules.team.router import router
from app.modules.team.schemas import TeamInviteRequest, TeamMemberSchema


class _OverrideTeamService:
    async def list_members(self, auth_context: AuthContext) -> list[TeamMemberSchema]:
        return [
            TeamMemberSchema(
                id="tm_owner",
                email="owner@example.com",
                display_name="Owner Name",
                role="owner",
                status="active",
                avatar_url=None,
                is_current_user=auth_context.user_id == "user_owner",
                is_registered_user=True,
                invited_by_name=None,
                created_at="2026-05-03T00:00:00+00:00",
            )
        ]

    async def invite_member(self, auth_context: AuthContext, payload: TeamInviteRequest) -> TeamMemberSchema:
        return TeamMemberSchema(
            id="tm_member",
            email=payload.email,
            display_name=None,
            role="member",
            status="invited",
            avatar_url=None,
            is_current_user=False,
            is_registered_user=False,
            invited_by_name="Owner Name",
            created_at="2026-05-03T00:00:00+00:00",
        )

    async def remove_member(self, auth_context: AuthContext, member_id: str) -> None:
        _ = (auth_context, member_id)


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/team")
    app.dependency_overrides[get_team_service] = lambda: _OverrideTeamService()
    return TestClient(app)


def _auth_headers() -> dict[str, str]:
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token(user_id='user_owner', roles=['owner'])}"}


def test_list_members_contract_returns_team_roster() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/team")
    app.dependency_overrides[get_team_service] = lambda: _OverrideTeamService()
    client = TestClient(app)

    response = client.get("/api/v1/team/members", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"][0]["email"] == "owner@example.com"
    assert payload["data"][0]["role"] == "owner"


def test_invite_member_contract_returns_team_member() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/team")
    app.dependency_overrides[get_team_service] = lambda: _OverrideTeamService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/team/members/invite",
        json={"email": "invitee@example.com"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["email"] == "invitee@example.com"
    assert payload["data"]["status"] == "invited"


def test_remove_member_contract_returns_success() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/team")
    app.dependency_overrides[get_team_service] = lambda: _OverrideTeamService()
    client = TestClient(app)

    response = client.delete("/api/v1/team/members/tm_member", headers=_auth_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["message"] == "success"
