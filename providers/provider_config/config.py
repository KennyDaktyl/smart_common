# smart_common/providers/provider_config/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderIntegrationSettings(BaseSettings):
    """
    Configuration for external provider integrations (Huawei, etc.).
    This is DOMAIN configuration, not application core config.
    """

    # ------------------------------------------------------------------
    # Huawei
    # ------------------------------------------------------------------
    HUAWEI_BASE_URL: str = Field(
        default="https://eu5.fusionsolar.huawei.com/thirdData",
        description="Base URL for Huawei FusionSolar API",
    )
    HUAWEI_TIMEOUT: float = Field(
        default=15.0,
        description="Default HTTP timeout for Huawei provider",
    )
    HUAWEI_MAX_RETRIES: int = Field(
        default=3,
        gt=0,
        description="Max retry attempts for Huawei API requests",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


provider_settings = ProviderIntegrationSettings()
