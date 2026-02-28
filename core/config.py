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
    POSTGRES_PASSWORD: SecretStr = SecretStr("postgres")

    DATABASE_URL_OVERRIDE: str | None = None

    # ------------------------------------------------------------------
    # Messaging / Cache
    # ------------------------------------------------------------------
    NATS_URL: str = "nats://nats:4222"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    STREAM_NAME: str = "device_communication"
    SUBJECT: str = "device_communication.*.event.provider_current_energy"

    # ------------------------------------------------------------------
    # Security (REQUIRED)
    # ------------------------------------------------------------------
    JWT_SECRET: SecretStr = SecretStr("dev-jwt-secret")
    # Must be 32 url-safe base64-encoded bytes for cryptography.Fernet
    FERNET_KEY: SecretStr = SecretStr("dev-jwt-secret")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AGENT_API_TOKEN: str = "token"

    # ------------------------------------------------------------------
    # Email / SMTP (REQUIRED)
    # ------------------------------------------------------------------
    EMAIL_HOST: str = "localhost"
    EMAIL_PORT: int = 587
    EMAIL_USER: str | None = None
    EMAIL_PASSWORD: SecretStr | None = None
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_FROM: str = "noreply@localhost"

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
