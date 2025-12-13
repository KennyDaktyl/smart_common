from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class CommonSettings(BaseSettings):
    LOG_DIR: str = Field("logs", env="LOG_DIR")

    POSTGRES_HOST: str = Field("db", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_NAME: str = Field("smartenergy", env="POSTGRES_NAME")
    POSTGRES_USER: str = Field("postgres", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("pass", env="POSTGRES_PASSWORD")

    NATS_URL: str = Field("nats://redis:4222", env="NATS_URL")

    REDIS_HOST: str = Field("redis", env="REDIS_HOST")
    REDIS_PORT: int = Field(6379, env="REDIS_PORT")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}"
        )

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        validate_default=True
    )

settings = CommonSettings()
