"""
应用配置模块
从环境变量或 .env 文件加载配置
包含：数据库、Redis、JWT、飞书、LLM 等配置项
"""
from functools import lru_cache
from pathlib import Path
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Eko"
    APP_VERSION: str = "v1.2"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    GENERATED_ROOT: str = str(Path(__file__).resolve().parent.parent / "generated")

    # Database
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "nexus_pilot"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_TASK_QUEUE: str = "aippt"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    JWT_ISSUER: str = "eko-auth"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    FRONTEND_STATIC_DIR: str | None = str(Path(__file__).resolve().parents[2] / "frontend")

    # Feishu
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_ENCRYPT_KEY: str = ""
    FEISHU_BASE_URL: str = "https://open.feishu.cn"
    FEISHU_AUTH_BASE_URL: str = "https://accounts.feishu.cn"
    FEISHU_OAUTH_REDIRECT_URI: str = "http://127.0.0.1:8010/frontend/test.html"
    FEISHU_OAUTH_SCOPE: str = "contact:user.base:readonly"
    FEISHU_OAUTH_STATE_TTL_SECONDS: int = 600
    FRONTEND_LOGIN_SUCCESS_URL: str = "http://127.0.0.1:8010/frontend/test.html"
    FEISHU_BITABLE_APP_TOKEN: str = ""
    FEISHU_BITABLE_TABLE_ID: str = ""
    FEISHU_BITABLE_FIELD_TITLE: str = "标题"
    FEISHU_BITABLE_FIELD_URL: str = "文档链接"

    # Agent (DeepSeek)
    AGENT_MODEL: str = "deepseek-v4-flash"
    AGENT_API_BASE: str = "https://api.deepseek.com"
    AGENT_API_KEY: str = ""

    # Volcengine (火山引擎) - 替代方案
    VOLCENGINE_API_KEY: str = ""
    VOLCENGINE_ENDPOINT: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCENGINE_MODEL: str = "ep-20260423222610-xbx2l"

    AGENT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    PPT_USE_LIVE_LLM: bool = False
    PPT_LLM_TIMEOUT_SECONDS: int = 180
    PPT_LLM_MAX_TOKENS: int = 16000
    PPT_EXPORT_NODE_BIN: str = "node"
    PPT_EXPORT_NODE_MODULES: str = ""
    PPT_EXPORT_VIEWPORT_WIDTH: int = 1600
    PPT_EXPORT_VIEWPORT_HEIGHT: int = 900
    PPT_EXPORT_DEVICE_SCALE_FACTOR: int = 2

    # AI PPT
    AIPPT_MODEL: str = "deepseek-v4-flash"
    AIPPT_API_BASE: str = "https://api.deepseek.com"
    AIPPT_API_KEY: str = ""
    AIPPT_STORAGE_DIR: str = "storage/aippt"
    AIPPT_VENDOR_DIR: str = "vendor/ppt-master"
    AIPPT_REDIS_QUEUE_ENABLED: bool = True
    AIPPT_UPLOADS_DIR: str = "storage/aippt/uploads"
    AIPPT_PROJECTS_DIR: str = "storage/aippt/projects"
    AIPPT_EXPORTS_DIR: str = "storage/aippt/exports"
    AIPPT_MAX_UPLOAD_MB: int = 25
    AIPPT_SLIDE_CONCURRENCY: int = 2
    AIPPT_THINKING_ENABLED: bool = False
    AIPPT_IMAGE_GENERATION_ENABLED: bool = False
    AIPPT_IMAGE_API_BASE: str = "https://www.packyapi.com"
    AIPPT_IMAGE_API_KEY: str = ""
    AIPPT_IMAGE_MODEL: str = "gpt-image-2"
    AIPPT_IMAGE_SIZE: str = "3840x2160"
    AIPPT_IMAGE_QUALITY: str = "high"
    AIPPT_IMAGE_OUTPUT_FORMAT: str = "png"
    AIPPT_IMAGE_TIMEOUT_SECONDS: int = 180

    @property
    def AIPPT_EFFECTIVE_API_KEY(self) -> str:
        return self.AIPPT_API_KEY or self.AGENT_API_KEY

    @property
    def AIPPT_STORAGE_PATH(self) -> Path:
        path = Path(self.AIPPT_STORAGE_DIR)
        if path.is_absolute():
            return path
        return BACKEND_DIR / path

    @property
    def AIPPT_UPLOADS_PATH(self) -> Path:
        path = Path(self.AIPPT_UPLOADS_DIR)
        if path.is_absolute():
            return path
        return BACKEND_DIR / path

    @property
    def AIPPT_PROJECTS_PATH(self) -> Path:
        path = Path(self.AIPPT_PROJECTS_DIR)
        if path.is_absolute():
            return path
        return BACKEND_DIR / path

    @property
    def AIPPT_EXPORTS_PATH(self) -> Path:
        path = Path(self.AIPPT_EXPORTS_DIR)
        if path.is_absolute():
            return path
        return BACKEND_DIR / path

    @property
    def AIPPT_VENDOR_PATH(self) -> Path:
        path = Path(self.AIPPT_VENDOR_DIR)
        if path.is_absolute():
            return path
        return REPO_ROOT / path

    @property
    def CELERY_EFFECTIVE_BROKER_URL(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def CELERY_EFFECTIVE_RESULT_BACKEND(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    model_config = ConfigDict(env_file=".env", extra="allow")


@lru_cache
def get_settings() -> Settings:
    return Settings()


class _SettingsProxy:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()
