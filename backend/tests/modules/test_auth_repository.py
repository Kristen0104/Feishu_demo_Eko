from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList, UnaryExpression

from app.modules.auth.models import FeishuAccount, FeishuOAuthToken, User
from app.modules.auth.repository import AuthRepository, FeishuIdentityUpsert, FeishuOAuthTokenUpsert


class _FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class _FakeSession:
    def __init__(self) -> None:
        self._storage: dict[type, list[object]] = {
            User: [],
            FeishuAccount: [],
            FeishuOAuthToken: [],
        }

    def add(self, obj: object) -> None:
        if getattr(obj, "id", None) is None:
            prefix = {
                User: "user",
                FeishuAccount: "fa",
                FeishuOAuthToken: "fot",
            }[type(obj)]
            setattr(obj, "id", f"{prefix}_{uuid4().hex}")
        self._storage[type(obj)].append(obj)

    async def flush(self) -> None:
        return None

    async def scalars(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        items = list(self._storage[entity])
        for criterion in statement._where_criteria:
            items = [item for item in items if self._matches(item, criterion)]
        order_clauses = list(statement._order_by_clauses)
        if order_clauses:
            order = order_clauses[0]
            reverse = isinstance(order, UnaryExpression) and getattr(order.modifier, "__name__", "") == "desc_op"
            sort_key = getattr(getattr(order, "element", order), "key", None)
            if sort_key:
                items.sort(key=lambda item: getattr(item, sort_key), reverse=reverse)
        return _FakeScalarResult(items)

    async def scalar(self, statement):
        return (await self.scalars(statement)).first()

    def _matches(self, item: object, criterion) -> bool:
        if isinstance(criterion, BooleanClauseList):
            if criterion.operator.__name__ == "or_":
                return any(self._matches(item, clause) for clause in criterion.clauses)
            return all(self._matches(item, clause) for clause in criterion.clauses)
        if isinstance(criterion, BinaryExpression):
            left = getattr(item, criterion.left.key)
            right = getattr(criterion.right, "value", None)
            return left == right
        raise AssertionError(f"unsupported criterion: {criterion!r}")


def test_upsert_feishu_identity_creates_and_updates_user_account_and_token() -> None:
    async def run_test() -> None:
        repository = AuthRepository(_FakeSession())
        expires_at = datetime.now(UTC) + timedelta(hours=2)

        created_user = await repository.upsert_feishu_identity(
            FeishuIdentityUpsert(
                open_id="ou_test",
                union_id="on_test",
                name="测试用户",
                avatar_url="https://example.com/avatar.png",
                tenant_key="tenant_1",
                email="tester@example.com",
                access_token="uat-1",
                refresh_token="urt-1",
                expires_at=expires_at,
                refresh_expires_at=expires_at + timedelta(days=30),
            )
        )

        updated_user = await repository.upsert_feishu_identity(
            FeishuIdentityUpsert(
                open_id="ou_test",
                union_id="on_test",
                name="新名字",
                avatar_url="https://example.com/new-avatar.png",
                tenant_key="tenant_1",
                email="tester@example.com",
                access_token="uat-2",
                refresh_token="urt-2",
                expires_at=expires_at + timedelta(hours=1),
                refresh_expires_at=expires_at + timedelta(days=31),
            )
        )

        account = await repository.get_feishu_account_by_user_id(created_user.id)
        latest_token = await repository.get_latest_token_by_user_id(created_user.id)

        assert created_user.id == updated_user.id
        assert updated_user.display_name == "新名字"
        assert account is not None
        assert account.open_id == "ou_test"
        assert latest_token is not None
        assert latest_token.access_token == "uat-2"

    asyncio.run(run_test())


def test_save_oauth_token_persists_latest_record() -> None:
    async def run_test() -> None:
        session = _FakeSession()
        user = User(
            id="user_123",
            display_name="测试用户",
            avatar_url=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(user)
        repository = AuthRepository(session)
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        token = await repository.save_oauth_token(
            user_id="user_123",
            token=FeishuOAuthTokenUpsert(
                access_token="uat-3",
                refresh_token="urt-3",
                expires_at=expires_at,
                refresh_expires_at=expires_at + timedelta(days=30),
                token_type="Bearer",
                scope=None,
            ),
        )

        latest = await repository.get_latest_token_by_user_id("user_123")
        assert token.id == latest.id
        assert latest.refresh_token == "urt-3"

    asyncio.run(run_test())
