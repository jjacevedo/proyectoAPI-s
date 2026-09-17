from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"

    synthesizer_provider: str = "openai"
    provider_timeout_seconds: float = Field(default=45, gt=0, le=300)
    max_tokens_per_request: int = Field(default=2048, gt=0, le=128000)
    max_prompt_chars: int = Field(default=12000, gt=100, le=100000)
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://multillm:multillm@postgres:5432/multillm"

    # Orden preferido para el router al elegir un subconjunto de providers
    # (de menor a mayor costo por millon de tokens segun pricing.py).
    provider_priority: str = "openai,gemini,anthropic"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def provider_priority_list(self) -> list[str]:
        return [name.strip() for name in self.provider_priority.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
