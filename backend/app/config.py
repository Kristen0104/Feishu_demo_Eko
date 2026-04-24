"""
应用配置模块
从环境变量或 .env 文件加载配置
包含：数据库、Redis、JWT、飞书、LLM 等配置项
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Eko"
    APP_VERSION: str = "v1.2"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

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
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:1420"]

    # Feishu
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_VERIFICATION_TOKEN: str = ""
    FEISHU_ENCRYPT_KEY: str = ""

    # Agent (DeepSeek)
    AGENT_MODEL: str = "deepseek"
    AGENT_API_BASE: str = "https://api.deepseek.com"
    AGENT_API_KEY: str = ""

    # Volcengine (火山引擎) - 替代方案
    VOLCENGINE_API_KEY: str = ""
    VOLCENGINE_ENDPOINT: str = "https://ark.cn-beijing.volces.com/api/v3"
    VOLCENGINE_MODEL: str = "ep-20260423222610-xbx2l"

    AGENT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
