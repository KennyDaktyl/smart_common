from functools import cached_property

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """
    Shared configuration for Smart Energy services.
    Loaded from environment variables.
    """

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------
    ENV: str = "development"
    BACKEND_PORT: int = 8000

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_DIR: str = "logs"

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_NAME: str = "smartenergy"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr

    DATABASE_URL_OVERRIDE: str | None = None

    # ------------------------------------------------------------------
    # Messaging / Cache
    # ------------------------------------------------------------------
    NATS_URL: str = "nats://nats:4222"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # ------------------------------------------------------------------
    # Security (REQUIRED)
    # ------------------------------------------------------------------
    JWT_SECRET: SecretStr
    FERNET_KEY: SecretStr

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # Email / SMTP (REQUIRED)
    # ------------------------------------------------------------------
    EMAIL_HOST: str
    EMAIL_PORT: int = 587
    EMAIL_USER: str | None = None
    EMAIL_PASSWORD: SecretStr | None = None
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_FROM: str

    DEFAULT_EMAIL: str | None = None

    FRONTEND_URL: str = "http://localhost:3000"

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @cached_property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    @cached_property
    def jwt_secret_str(self) -> str:
        return self.JWT_SECRET.get_secret_value()

    @cached_property
    def fernet_key_bytes(self) -> bytes:
        return self.FERNET_KEY.get_secret_value().encode()

    # ------------------------------------------------------------------
    # Settings config
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = CommonSettings()  # type: ignore[call-arg]
