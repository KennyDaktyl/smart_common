from functools import cached_property

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """
    Shared configuration for Smart Energy services.

    Values are loaded from environment variables
    and can be overridden per service.
    """

    ENV: str = Field("development", env="ENV")
    BACKEND_PORT: int = Field(8000, env="PORT")
    
    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_DIR: str = Field("logs", env="LOG_DIR")

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = Field("db", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_NAME: str = Field("smartenergy", env="POSTGRES_NAME")
    POSTGRES_USER: str = Field("postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: SecretStr = Field("pass", env="POSTGRES_PASSWORD")

    DATABASE_URL_OVERRIDE: str | None = Field(
        default=None,
        env="DATABASE_URL",
        description="Optional full database URL override (e.g. for cloud providers)",
    )

    # ------------------------------------------------------------------
    # Messaging / Cache
    # ------------------------------------------------------------------
    NATS_URL: str = Field("nats://nats:4222", env="NATS_URL")

    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    JWT_SECRET: SecretStr = Field(
        ...,
        env="JWT_SECRET",
        description="JWT signing secret (HS256)",
    )
    FERNET_KEY: SecretStr = Field(
        ...,
        env="FERNET_KEY",
        description="Fernet encryption key (base64, 32 bytes)",
    )

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # ------------------------------------------------------------------
    # Email / SMTP
    # ------------------------------------------------------------------
    EMAIL_HOST: str = Field(..., env="EMAIL_HOST")
    EMAIL_PORT: int = Field(587, env="EMAIL_PORT")
    EMAIL_USER: str | None = Field(None, env="EMAIL_USER")
    EMAIL_PASSWORD: SecretStr | None = Field(None, env="EMAIL_PASSWORD")
    EMAIL_USE_TLS: bool = Field(True, env="EMAIL_USE_TLS")
    EMAIL_USE_SSL: bool = Field(False, env="EMAIL_USE_SSL")
    EMAIL_FROM: str = Field(..., env="EMAIL_FROM")

    DEFAULT_EMAIL: str | None = Field(None, env="DEFAULT_EMAIL")

    FRONTEND_URL: str = Field(
        "http://localhost:3000",
        env="FRONTEND_URL",
        description="Frontend base URL (used in email links)",
    )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @cached_property
    def DATABASE_URL(self) -> str:
        """
        Full SQLAlchemy-compatible database URL.
        Prefers DATABASE_URL env if provided.
        """
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    # ------------------------------------------------------------------
    # Security – normalized values
    # ------------------------------------------------------------------
    @cached_property
    def jwt_secret_str(self) -> str:
        """
        JWT secret as plain string (for python-jose).
        """
        return self.JWT_SECRET.get_secret_value()

    @cached_property
    def fernet_key_bytes(self) -> bytes:
        """
        Fernet key as bytes (for cryptography.Fernet).
        """
        return self.FERNET_KEY.get_secret_value().encode()

    # ------------------------------------------------------------------
    # Pydantic settings config
    # ------------------------------------------------------------------
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )


settings = CommonSettings()
