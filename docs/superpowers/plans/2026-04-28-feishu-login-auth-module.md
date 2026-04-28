# 飞书登录模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 `/api/v1/auth/feishu/login` stub 升级为真实飞书 OAuth 登录闭环：Redis 校验授权 `state`，PostgreSQL 持久化用户与飞书授权，后端签发 JWT，前端只保留测试入口。

**Architecture:** 主后端开发交给 `subagent gpt5.4`：负责数据库模型、OAuth provider、JWT 鉴权、Redis state 和 token 刷新能力。简单测试、读代码、验收清单交给 `subagent gpt5.4mini`：负责补契约测试、mock 飞书 API、验证现有路由影响。后续“邀请飞书好友加入对话”不在本期实现，但本期必须沉淀 `FeishuUserTokenService`，让后续邀请能力能复用用户授权 token。

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy async, PostgreSQL, Redis, python-jose, httpx, pytest, FastAPI TestClient, 一个静态 HTML 测试页。

---

## 一、文件结构与职责

- Modify: `backend/app/config.py` — 增加飞书 OAuth、JWT issuer、前端回跳 URL、Redis state TTL 配置。
- Create: `backend/app/modules/auth/models.py` — PostgreSQL ORM 模型：本地用户、飞书账号、飞书 OAuth token。
- Modify: `backend/app/core/database.py` — 确保 auth models 被 `Base.metadata.create_all` 发现。
- Create: `backend/app/modules/auth/repository.py` — 用户、飞书账号、OAuth token 的 upsert / query。
- Modify: `backend/app/modules/auth/schemas.py` — 登录 URL、callback/login、token、用户资料 schema。
- Modify: `backend/app/modules/auth/provider.py` — 真实飞书 OAuth code exchange、refresh、userinfo client。
- Modify: `backend/app/modules/auth/service.py` — Redis state 校验、DB upsert、JWT 签发、当前用户查询。
- Modify: `backend/app/modules/auth/dependencies.py` — 注入 DB session、Redis、provider、repository、service。
- Modify: `backend/app/modules/auth/router.py` — 增加 login-url/callback，保留现有 login contract 兼容测试页。
- Modify: `backend/app/core/security.py` — Bearer JWT 解析，生成真实 `AuthContext`。
- Create: `backend/app/modules/feishu/user_token_service.py` — 后续邀请好友复用的用户 token 获取和刷新服务。
- Create: `backend/tests/modules/test_auth_feishu_oauth_contract.py` — 登录 URL、state、callback、JWT、`/me` 契约测试。
- Create: `backend/tests/modules/test_auth_repository.py` — PostgreSQL repository upsert 测试。
- Create: `backend/tests/modules/test_feishu_user_token_service.py` — 用户飞书 token 读取/刷新测试。
- Modify: `backend/tests/conftest.py` — 测试环境隔离飞书、Redis、数据库依赖。
- Modify: `API.md` — 记录真实登录流程与测试方式。
- Modify: `frontend/test.html` — 仅增加飞书登录测试区，不建设正式前端产品 UI。

---

## 二、实施任务

### Task 1: 锁定登录 API 契约

**Owner:** `subagent gpt5.4mini`

**Files:**
- Create: `backend/tests/modules/test_auth_feishu_oauth_contract.py`
- Modify: `backend/tests/modules/test_module_registration.py`
- Modify: `backend/app/modules/auth/schemas.py`
- Modify: `backend/app/modules/auth/router.py`

- [ ] **Step 1: 写失败测试定义登录入口、state 和 callback 契约**

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.auth.router import router


def _build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    return TestClient(app)


def test_feishu_login_url_returns_authorize_url_and_state() -> None:
    client = _build_client()

    response = client.get("/api/v1/auth/feishu/login-url?redirect_uri=http://localhost:8000/frontend/test.html")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["state"]
    assert payload["authorize_url"].startswith("https://open.feishu.cn/open-apis/authen/v1/authorize")
    assert "redirect_uri=" in payload["authorize_url"]
    assert "state=" in payload["authorize_url"]


def test_feishu_callback_requires_code_and_state() -> None:
    client = _build_client()

    response = client.get("/api/v1/auth/feishu/callback")

    assert response.status_code == 422
```

- [ ] **Step 2: 运行测试确认当前失败**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_feishu_oauth_contract.py -v
```
Expected: FAIL，因为 `/feishu/login-url` 和 `/feishu/callback` 尚未实现。

- [ ] **Step 3: 增加 schema 与路由骨架**

```python
class FeishuLoginUrlSchema(BaseModel):
    authorize_url: str
    state: str
    expires_in: int


class FeishuCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: str | None = None
```

```python
@router.get(
    "/feishu/login-url",
    response_model=ApiResponse[FeishuLoginUrlSchema],
    summary="生成飞书登录授权 URL",
)
async def get_feishu_login_url(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    redirect_uri: str | None = None,
) -> ApiResponse[FeishuLoginUrlSchema]:
    return ApiResponse.success(await auth_service.create_feishu_login_url(redirect_uri=redirect_uri))


@router.get(
    "/feishu/callback",
    response_model=ApiResponse[AuthTokenSchema],
    summary="飞书 OAuth 回调登录",
)
async def feishu_callback(
    code: str,
    state: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    redirect_uri: str | None = None,
) -> ApiResponse[AuthTokenSchema]:
    return ApiResponse.success(
        await auth_service.login_with_feishu_callback(
            FeishuCallbackRequest(code=code, state=state, redirect_uri=redirect_uri)
        )
    )
```

- [ ] **Step 4: 更新模块注册测试**

在 `backend/tests/modules/test_module_registration.py` 预期路由中加入：
```python
"/api/v1/auth/feishu/login-url": {"GET"},
"/api/v1/auth/feishu/callback": {"GET"},
```

- [ ] **Step 5: 运行契约测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_feishu_oauth_contract.py tests/modules/test_module_registration.py -v
```
Expected: 新路由 contract 通过；真实 callback 可先因 service 未完成而在后续任务补齐。

### Task 2: 建立 PostgreSQL 认证模型

**Owner:** `subagent gpt5.4`

**Files:**
- Create: `backend/app/modules/auth/models.py`
- Create: `backend/app/modules/auth/repository.py`
- Create: `backend/tests/modules/test_auth_repository.py`
- Modify: `backend/app/core/database.py`

- [ ] **Step 1: 写 repository upsert 测试**

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.auth.repository import AuthRepository, FeishuIdentityUpsert


@pytest.mark.asyncio
async def test_upsert_feishu_identity_creates_user_and_account(db_session) -> None:
    repository = AuthRepository(db_session)

    user = await repository.upsert_feishu_identity(
        FeishuIdentityUpsert(
            open_id="ou_test",
            union_id="on_test",
            name="测试用户",
            avatar_url="https://example.com/avatar.png",
            access_token="uat-test",
            refresh_token="urt-test",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
    )

    assert user.id
    assert user.display_name == "测试用户"
    account = await repository.get_feishu_account_by_user_id(user.id)
    assert account.open_id == "ou_test"
```

- [ ] **Step 2: 运行测试确认缺少模型和 fixture**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_repository.py -v
```
Expected: FAIL，提示 `AuthRepository` 或 `db_session` 不存在。

- [ ] **Step 3: 新增 ORM 模型**

```python
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"user_{uuid4().hex}")
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    feishu_account: Mapped["FeishuAccountModel"] = relationship(back_populates="user")


class FeishuAccountModel(Base):
    __tablename__ = "feishu_accounts"
    __table_args__ = (
        UniqueConstraint("open_id", name="uq_feishu_accounts_open_id"),
        UniqueConstraint("union_id", name="uq_feishu_accounts_union_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"fa_{uuid4().hex}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    open_id: Mapped[str] = mapped_column(String(255), nullable=False)
    union_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tenant_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[UserModel] = relationship(back_populates="feishu_account")


class FeishuOAuthTokenModel(Base):
    __tablename__ = "feishu_oauth_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"fot_{uuid4().hex}")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    access_token: Mapped[str] = mapped_column(String(4096), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

- [ ] **Step 4: 让模型进入 metadata**

在 `backend/app/core/database.py` 导入模型模块：
```python
def import_models() -> None:
    import app.modules.auth.models  # noqa: F401


async def init_db():
    import_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5: 实现 repository**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import FeishuAccountModel, FeishuOAuthTokenModel, UserModel


@dataclass(frozen=True)
class FeishuIdentityUpsert:
    open_id: str
    union_id: str | None
    name: str
    avatar_url: str | None
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    tenant_key: str | None = None


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_feishu_identity(self, identity: FeishuIdentityUpsert) -> UserModel:
        now = datetime.now(UTC)
        account = await self.get_feishu_account_by_open_id(identity.open_id)
        if account:
            user = account.user
            user.display_name = identity.name
            user.avatar_url = identity.avatar_url
            user.updated_at = now
            account.union_id = identity.union_id
            account.tenant_key = identity.tenant_key
            account.updated_at = now
        else:
            user = UserModel(display_name=identity.name, avatar_url=identity.avatar_url, created_at=now, updated_at=now)
            self._session.add(user)
            await self._session.flush()
            account = FeishuAccountModel(
                user_id=user.id,
                open_id=identity.open_id,
                union_id=identity.union_id,
                tenant_key=identity.tenant_key,
                created_at=now,
                updated_at=now,
            )
            self._session.add(account)

        token = FeishuOAuthTokenModel(
            user_id=user.id,
            access_token=identity.access_token,
            refresh_token=identity.refresh_token,
            expires_at=identity.expires_at,
            created_at=now,
            updated_at=now,
        )
        self._session.add(token)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_user_by_id(self, user_id: str) -> UserModel | None:
        return await self._session.get(UserModel, user_id)

    async def get_feishu_account_by_open_id(self, open_id: str) -> FeishuAccountModel | None:
        result = await self._session.execute(select(FeishuAccountModel).where(FeishuAccountModel.open_id == open_id))
        return result.scalar_one_or_none()

    async def get_feishu_account_by_user_id(self, user_id: str) -> FeishuAccountModel | None:
        result = await self._session.execute(select(FeishuAccountModel).where(FeishuAccountModel.user_id == user_id))
        return result.scalar_one_or_none()
```

- [ ] **Step 6: 运行 repository 测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_repository.py -v
```
Expected: PASS。

### Task 3: 接入 Redis OAuth state

**Owner:** `subagent gpt5.4`

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/modules/auth/service.py`
- Modify: `backend/app/modules/auth/dependencies.py`
- Modify: `backend/tests/modules/test_auth_feishu_oauth_contract.py`

- [ ] **Step 1: 写 state 一次性校验测试**

```python
def test_feishu_callback_rejects_reused_state() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/auth")
    app.dependency_overrides[get_auth_service] = lambda: AuthService(
        provider=SuccessfulFakeFeishuProvider(),
        repository=InMemoryAuthRepository(),
        redis=InMemoryRedis({"feishu:oauth:state:state-123": "http://localhost/callback"}),
        settings=Settings(SECRET_KEY="test-secret"),
    )
    client = TestClient(app)

    first = client.get("/api/v1/auth/feishu/callback?code=code-123&state=state-123")
    second = client.get("/api/v1/auth/feishu/callback?code=code-123&state=state-123")

    assert first.status_code == 200
    assert second.status_code == 400
```

- [ ] **Step 2: 增加配置**

```python
FEISHU_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/feishu/callback"
FEISHU_OAUTH_STATE_TTL_SECONDS: int = 600
FRONTEND_LOGIN_SUCCESS_URL: str = "http://localhost:8000/frontend/test.html"
JWT_ISSUER: str = "eko"
```

- [ ] **Step 3: 实现 state 写入与消费**

```python
async def create_feishu_login_url(self, redirect_uri: str | None = None) -> FeishuLoginUrlSchema:
    state = secrets.token_urlsafe(24)
    callback_url = redirect_uri or self._settings.FEISHU_OAUTH_REDIRECT_URI
    await self._redis.set(f"feishu:oauth:state:{state}", callback_url, ex=self._settings.FEISHU_OAUTH_STATE_TTL_SECONDS)
    return FeishuLoginUrlSchema(
        authorize_url=self._provider.build_authorize_url(state=state, redirect_uri=callback_url),
        state=state,
        expires_in=self._settings.FEISHU_OAUTH_STATE_TTL_SECONDS,
    )


async def _consume_state(self, state: str) -> str:
    key = f"feishu:oauth:state:{state}"
    redirect_uri = await self._redis.get(key)
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="Invalid or expired Feishu OAuth state")
    await self._redis.delete(key)
    return redirect_uri
```

- [ ] **Step 4: 运行 state 测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_feishu_oauth_contract.py -v
```
Expected: PASS。

### Task 4: 实现真实飞书 OAuth provider

**Owner:** `subagent gpt5.4`

**Files:**
- Modify: `backend/app/modules/auth/provider.py`
- Modify: `backend/app/modules/auth/schemas.py`
- Create: `backend/tests/modules/test_auth_feishu_provider.py`

- [ ] **Step 1: 写 httpx mock 测试**

```python
def test_exchange_code_maps_feishu_token_and_userinfo() -> None:
    provider = FeishuOAuthProvider(
        settings=Settings(FEISHU_APP_ID="cli_xxx", FEISHU_APP_SECRET="secret"),
        http_client=MockFeishuHttpClient(
            token_payload={"access_token": "uat-1", "refresh_token": "urt-1", "expires_in": 7200},
            userinfo_payload={
                "open_id": "ou_1",
                "union_id": "on_1",
                "name": "测试用户",
                "avatar_url": "https://example.com/a.png",
                "tenant_key": "tenant_1",
            },
        ),
    )

    identity = await provider.exchange_code(code="code-1", redirect_uri="http://localhost/callback")

    assert identity.open_id == "ou_1"
    assert identity.union_id == "on_1"
    assert identity.access_token == "uat-1"
    assert identity.refresh_token == "urt-1"
```

- [ ] **Step 2: 定义 provider 返回对象**

```python
class FeishuOAuthIdentity(BaseModel):
    open_id: str
    union_id: str | None = None
    tenant_key: str | None = None
    name: str
    avatar_url: str | None = None
    access_token: str
    refresh_token: str | None = None
    expires_in: int
```

- [ ] **Step 3: provider 实现接口**

```python
class FeishuOAuthProviderProtocol(Protocol):
    def build_authorize_url(self, *, state: str, redirect_uri: str) -> str: ...
    async def exchange_code(self, *, code: str, redirect_uri: str) -> FeishuOAuthIdentity: ...
    async def refresh_access_token(self, *, refresh_token: str) -> FeishuOAuthIdentity: ...
```

- [ ] **Step 4: 运行 provider 测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_feishu_provider.py -v
```
Expected: PASS，且不访问真实网络。

### Task 5: 签发 JWT 并替换 stub 鉴权

**Owner:** `subagent gpt5.4`

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/modules/auth/service.py`
- Modify: `backend/app/modules/auth/router.py`
- Modify: `backend/tests/modules/test_auth_contract.py`
- Modify: `backend/tests/modules/test_auth_feishu_oauth_contract.py`

- [ ] **Step 1: 写 JWT 和 `/auth/me` 测试**

```python
def test_current_user_requires_bearer_token() -> None:
    client = _build_client()

    response = client.get("/api/v1/auth/me")

    assert response.status_code in {401, 403}
```

```python
def test_current_user_returns_database_user_for_valid_jwt() -> None:
    client = _build_client_with_seeded_user(
        user_id="user_123",
        display_name="测试用户",
        feishu_open_id="ou_123",
    )
    token = create_access_token(
        user_id="user_123",
        expires_delta=timedelta(minutes=30),
        settings=Settings(SECRET_KEY="test-secret"),
    )

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["user_id"] == "user_123"
    assert payload["display_name"] == "测试用户"
    assert payload["feishu_user_id"] == "ou_123"
```

- [ ] **Step 2: 实现 JWT create/parse**

```python
def create_access_token(*, user_id: str, expires_delta: timedelta, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

- [ ] **Step 3: 替换 `get_auth_context`**

```python
async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=True))],
) -> AuthContext:
    payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return AuthContext(user_id=payload["sub"], roles=["user"])
```

- [ ] **Step 4: 修改 `/auth/me` 从 DB 查询真实用户**

`AuthService.get_current_user` 改为 async，通过 `AuthRepository.get_user_by_id` 和 `get_feishu_account_by_user_id` 返回真实资料。

- [ ] **Step 5: 运行 auth 测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_auth_contract.py tests/modules/test_auth_feishu_oauth_contract.py -v
```
Expected: PASS；旧 stub 断言需要更新为真实 JWT 行为。

### Task 6: 沉淀飞书用户 token 服务

**Owner:** `subagent gpt5.4`

**Files:**
- Create: `backend/app/modules/feishu/user_token_service.py`
- Create: `backend/tests/modules/test_feishu_user_token_service.py`
- Modify: `backend/app/modules/feishu/dependencies.py`

- [ ] **Step 1: 写 token 获取测试**

```python
@pytest.mark.asyncio
async def test_get_valid_user_access_token_returns_stored_token_when_not_expired() -> None:
    service = FeishuUserTokenService(repository=repository, provider=provider, redis=redis)

    token = await service.get_valid_user_access_token("user_123")

    assert token == "uat-current"
```

- [ ] **Step 2: 写 token 过期刷新测试**

```python
@pytest.mark.asyncio
async def test_get_valid_user_access_token_refreshes_expired_token_once() -> None:
    service = FeishuUserTokenService(repository=repository, provider=provider, redis=redis)

    token = await service.get_valid_user_access_token("user_123")

    assert token == "uat-refreshed"
```

- [ ] **Step 3: 实现服务边界**

```python
class FeishuUserTokenService:
    def __init__(self, repository: AuthRepository, provider: FeishuOAuthProviderProtocol, redis) -> None:
        self._repository = repository
        self._provider = provider
        self._redis = redis

    async def get_valid_user_access_token(self, user_id: str) -> str:
        token = await self._repository.get_latest_feishu_oauth_token(user_id)
        if token and token.expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return token.access_token
        return await self._refresh_with_lock(user_id)
```

- [ ] **Step 4: 运行 token service 测试**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules/test_feishu_user_token_service.py -v
```
Expected: PASS。

### Task 7: 前端测试页只做登录验证

**Owner:** `subagent gpt5.4`

**Files:**
- Modify: `frontend/test.html`
- Modify: `API.md`

- [ ] **Step 1: 在测试页增加最小登录区**

页面只需要：
- “获取飞书登录 URL”
- “打开飞书授权”
- “手动粘贴 code/state 并换 token”
- “调用 `/api/v1/auth/me`”
- 显示 access token、用户信息、错误信息

- [ ] **Step 2: 增加测试页脚本**

```javascript
async function getFeishuLoginUrl() {
  const response = await fetch("/api/v1/auth/feishu/login-url?redirect_uri=" + encodeURIComponent(window.location.href));
  const payload = await response.json();
  localStorage.setItem("eko_feishu_oauth_state", payload.data.state);
  document.querySelector("#feishu-login-url").value = payload.data.authorize_url;
}

async function exchangeFeishuCode() {
  const code = document.querySelector("#feishu-code").value.trim();
  const state = document.querySelector("#feishu-state").value.trim();
  const response = await fetch("/api/v1/auth/feishu/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({code, state})
  });
  const payload = await response.json();
  localStorage.setItem("eko_access_token", payload.data.access_token);
  renderLoginResult(payload);
}
```

- [ ] **Step 3: 更新 API 文档**

记录：
- `GET /api/v1/auth/feishu/login-url`
- `GET /api/v1/auth/feishu/callback`
- `POST /api/v1/auth/feishu/login`
- `GET /api/v1/auth/me`
- Redis state key：`feishu:oauth:state:{state}`
- PostgreSQL 表：`users`、`feishu_accounts`、`feishu_oauth_tokens`

- [ ] **Step 4: 浏览器手动验收**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/uvicorn app.main:app --reload
```
Expected:
- 打开 `/frontend/test.html`
- 能生成飞书授权 URL
- 使用真实 code 后能拿到 JWT
- `/auth/me` 能返回真实用户

### Task 8: 集成验收与回归测试

**Owner:** `subagent gpt5.4mini`

**Files:**
- Modify: `backend/tests/conftest.py`
- Modify: `API.md`

- [ ] **Step 1: 汇总测试命令**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest \
  tests/modules/test_auth_contract.py \
  tests/modules/test_auth_feishu_oauth_contract.py \
  tests/modules/test_auth_feishu_provider.py \
  tests/modules/test_auth_repository.py \
  tests/modules/test_feishu_user_token_service.py \
  tests/modules/test_module_registration.py \
  -v
```

- [ ] **Step 2: 运行更广范围回归**

Run:
```bash
cd /Users/klot/Feishu_demo_Eko/backend && .venv/bin/pytest tests/modules tests/test_app_routes.py -v
```

- [ ] **Step 3: 验收标准**

必须满足：
- Redis 中 OAuth state 一次性消费。
- PostgreSQL 中用户、飞书账号、token 可持久化。
- JWT 能保护 `/auth/me`。
- 飞书 API 在测试中全部 mock，不访问真实网络。
- 前端只作为测试页，不引入完整登录产品 UI。
- `FeishuUserTokenService` 可被后续邀请好友功能复用。

---

## 三、风险与约束

- 真实飞书 OAuth endpoint、scope 和 userinfo 字段需以当前飞书开放平台配置为准；实现前由 `subagent gpt5.4mini` 做一次官方文档核对。
- 当前仓库已有未提交变更，执行前不要覆盖无关文件，尤其是 `ppt` 模块和 `frontend/test.html` 的既有改动。
- 如果没有迁移工具，本期可先使用 `Base.metadata.create_all`，但生产化前建议补 Alembic。
- OAuth token 存储当前按明文计划落库；若进入真实生产环境，应增加字段级加密。

## 四、自查结果

- Spec coverage: 覆盖飞书登录、Redis、PostgreSQL、JWT、测试页、后续邀请好友 token 复用。
- Placeholder scan: 没有占位任务或空任务；所有任务都有明确文件、命令和期望结果。
- Type consistency: `FeishuLoginUrlSchema`、`FeishuCallbackRequest`、`FeishuOAuthIdentity`、`FeishuUserTokenService` 命名在任务间保持一致。
