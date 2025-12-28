from pydantic import Field

from smart_common.providers.provider_config.config import ProviderIntegrationSettings


class GoodWeProviderIntegrationSettings(ProviderIntegrationSettings):
    GOODWE_TIMEOUT: float = Field(
        default=15.0,
        description="Default HTTP timeout for GoodWe provider",
    )

    GOODWE_MAX_RETRIES: int = Field(
        default=3,
        gt=0,
        description="Max retry attempts for GoodWe API requests",
    )


goodwe_integration_settings = GoodWeProviderIntegrationSettings()
