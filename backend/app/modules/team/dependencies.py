from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import get_auth_repository
from app.modules.auth.repository import AuthRepository
from app.modules.team.repository import TeamRepository
from app.modules.team.service import TeamService


def get_team_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> TeamRepository:
    return TeamRepository(db)


def get_team_service(
    repository: Annotated[TeamRepository, Depends(get_team_repository)],
    auth_repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> TeamService:
    return TeamService(repository, auth_repository)

