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
    gemini_model: str = "gemini-3.1-flash-lite"
    groq_api_key: str | None = None
    # Verificar en console.groq.com antes de depender de este ID en produccion:
    # los nombres de modelo de Groq cambian con el tiempo.
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_api_key: str | None = None
    cerebras_model: str = "gpt-oss-120b"

    synthesizer_provider: str = "cerebras"
    enable_cross_critique: bool = True
    enable_reevaluation_round: bool = True
    enable_code_verification: bool = True
    code_execution_timeout_seconds: float = Field(default=5, gt=0, le=60)
    code_max_output_chars: int = Field(default=4000, gt=0, le=100000)
    provider_timeout_seconds: float = Field(default=45, gt=0, le=300)
    max_tokens_per_request: int = Field(default=2048, gt=0, le=128000)
    max_prompt_chars: int = Field(default=12000, gt=100, le=100000)
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://multillm:multillm@postgres:5432/multillm"

    # Orden preferido para el router al elegir un subconjunto de providers.
    # cerebras/gemini/groq son gratuitos por defecto; openai queda al final
    # como respaldo (solo se usa si el router necesita mas providers de los
    # que hay gratis disponibles, o si a alguno le falta la api key). anthropic
    # no esta en la lista por defecto (issue #17: se quedo sin credito) pero
    # sigue disponible si se le agrega una api key y se reintroduce aqui.
    provider_priority: str = "cerebras,gemini,groq,openai"

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
