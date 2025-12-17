from functools import cached_property

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CommonSettings(BaseSettings):
    """
    Shared configuration for Smart Energy services.
    Values can be overridden per-service via environment variables.
    """

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_DIR: str = Field("logs", env="LOG_DIR")

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = Field("db", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_NAME: str = Field("smartenergy", env="POSTGRES_NAME")
    POSTGRES_USER: str = Field("postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: SecretStr = Field("pass", env="POSTGRES_PASSWORD")

    DATABASE_URL_OVERRIDE: str | None = Field(
        default=None,
        env="DATABASE_URL",
        description="Optional full database URL override",
    )

    # ------------------------------------------------------------------
    # Messaging / Cache
    # ------------------------------------------------------------------
    NATS_URL: str = Field("nats://redis:4222", env="NATS_URL")

    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    JWT_SECRET: SecretStr = Field(..., env="JWT_SECRET")
    FERNET_KEY: SecretStr = Field(..., env="FERNET_KEY")

    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, env="REFRESH_TOKEN_EXPIRE_DAYS")

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @cached_property
    def DATABASE_URL(self) -> str:
        """
        Returns full database URL.
        Prefers DATABASE_URL env if provided.
        """
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE

        password = self.POSTGRES_PASSWORD.get_secret_value()
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True,
    )


settings = CommonSettings()
