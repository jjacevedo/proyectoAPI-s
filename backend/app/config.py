from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-luna"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    # El secret real en GitHub Actions/entornos de este proyecto se llama
    # ROQ_API_KEY (typo de nacimiento, dejado asi a proposito por el dueño
    # del repo en vez de renombrarlo) -- el alias hace que el campo interno
    # se siga llamando groq_api_key/GROQ_API_KEY para quien lea el codigo,
    # pero lea la variable de entorno real ROQ_API_KEY.
    groq_api_key: str | None = Field(default=None, validation_alias="ROQ_API_KEY")
    # "llama-3.3-70b-versatile" fue el default original, pero Groq lo movio a
    # tier Enterprise (ya no responde con una key de developer/free) el 17 de
    # junio de 2026 -- confirmado con un 404 model_not_found real en produccion.
    # Groq recomienda migrar a "openai/gpt-oss-120b". Verificar en
    # console.groq.com/docs/models antes de depender de este nuevo default:
    # los nombres de modelo de Groq cambian con frecuencia.
    groq_model: str = "openai/gpt-oss-120b"
    cerebras_api_key: str | None = None
    cerebras_model: str = "gpt-oss-120b"
    nvidia_api_key: str | None = None
    # build.nvidia.com (NIM) -- verificar el ID de modelo vigente en la
    # consola antes de depender de este default en produccion.
    nvidia_model: str = "meta/llama-3.1-70b-instruct"

    synthesizer_provider: str = "cerebras"
    enable_cross_critique: bool = True
    enable_reevaluation_round: bool = True
    enable_code_verification: bool = True
    code_execution_timeout_seconds: float = Field(default=5, gt=0, le=60)
    code_max_output_chars: int = Field(default=4000, gt=0, le=100000)
    enable_calculation_verification: bool = True
    # Tolerancia RELATIVA al comparar el numero final de un candidato contra
    # el valor de referencia calculado por el sandbox (ver calculation_verifier.py).
    calculation_tolerance: float = Field(default=1e-6, gt=0, le=1)
    enable_fact_search: bool = True
    fact_search_max_queries: int = Field(default=3, gt=0, le=5)
    fact_search_timeout_seconds: float = Field(default=10, gt=0, le=60)
    # Idioma de Wikipedia consultado (subdominio, ej. "es", "en").
    wikipedia_language: str = "es"
    # Framework de evaluacion 1-LLM vs N-LLM (issue #14, POST /api/evaluate).
    enable_evaluation_judge: bool = True
    # Provider que actua como juez comparando ambas respuestas. Si no esta
    # configurado o no esta disponible, se usa el mismo que synthesizer_provider.
    evaluation_judge_provider: str | None = None
    # Memoria de conversaciones (issue #16): cuantos mensajes previos (usuario
    # + asistente) se incluyen como contexto en el prompt enviado a los
    # providers. Un numero acotado evita que una conversacion larga infle el
    # consumo de tokens sin limite.
    conversation_history_max_messages: int = Field(default=10, gt=0, le=50)
    # Rate limiting y control de presupuesto (Fase 2 pendiente, cerrado aqui).
    # Ambos quedan DESACTIVADOS por defecto: es un proyecto de un solo
    # desarrollador corriendo localmente/en CI, y un limite activo por
    # defecto podria autobloquear pruebas o el propio desarrollo. Se activan
    # explicitamente por variable de entorno cuando haya trafico real.
    enable_rate_limiting: bool = False
    rate_limit_requests_per_minute: int = Field(default=20, gt=0, le=10000)
    # Si se define, /api/chat y /api/evaluate devuelven 402 una vez que el
    # costo estimado ya persistido hoy (UTC, sumando request_logs y
    # evaluation_logs) alcanza este monto. None = sin limite (por defecto).
    daily_budget_usd: float | None = Field(default=None, gt=0)
    provider_timeout_seconds: float = Field(default=45, gt=0, le=300)
    max_tokens_per_request: int = Field(default=2048, gt=0, le=128000)
    max_prompt_chars: int = Field(default=12000, gt=100, le=100000)
    cors_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://multillm:multillm@postgres:5432/multillm"

    # Orden preferido para el router al elegir un subconjunto de providers.
    # cerebras/gemini/groq/nvidia son gratuitos por defecto; openai queda al
    # final como respaldo (solo se usa si el router necesita mas providers de
    # los que hay gratis disponibles, o si a alguno le falta la api key).
    # anthropic no esta en la lista por defecto (issue #17: se quedo sin
    # credito) pero sigue disponible si se le agrega una api key y se
    # reintroduce aqui.
    provider_priority: str = "cerebras,gemini,groq,nvidia,openai"

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
