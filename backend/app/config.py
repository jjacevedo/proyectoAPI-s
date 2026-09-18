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
    # 4 intentos previos, los 4 fallaron con evidencia real de la API
    # (nunca adivinados sin confirmar despues):
    #   1. "meta/llama-3.1-70b-instruct"        -> 410 Gone (EOL 2026-08-26)
    #   2. "meta/llama-3.3-70b-instruct"        -> 410 Gone (EOL 2026-08-26)
    #   3. "meta/llama-4-scout-17b-16e-instruct" -> 404 Not Found
    #   4. "meta/llama-4-maverick-17b-128e-instruct" -> 410 Gone (EOL
    #      2026-07-27), pese a venir de busqueda web como "modelo destacado".
    # Quinto intento, mejor evidencia esta vez: "z-ai/glm-5.3", copiado
    # directo de un ejemplo de codigo real generado por build.nvidia.com
    # (panel "Try it" de la propia pagina del modelo, con SDK de OpenAI
    # igual al que usa este provider) -- AUN SIN CONFIRMAR con una llamada
    # real, pendiente de verificar en CI.
    nvidia_model: str = "z-ai/glm-5.3"
    opencode_api_key: str | None = None
    # opencode.ai/zen: "big-pickle" es un modelo gratis por tiempo limitado
    # (promocional, no un tier gratuito permanente) -- verificar en
    # opencode.ai/docs/zen que siga disponible antes de depender de este
    # default en produccion.
    opencode_model: str = "big-pickle"

    synthesizer_provider: str = "gemini"
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
    # gemini/groq son los proveedores gratuitos confirmados funcionando en
    # produccion real; nvidia/opencode quedan disponibles pero sin modelo
    # confirmado (nvidia) o bloqueados por su propio tier gratis (opencode:
    # 403 FreeTierError, solo acepta llamadas desde su propio cliente) --
    # ver docs/ARQUITECTURA.md. openai queda al final como respaldo de pago.
    # cerebras NO esta en la lista por defecto: su cuenta gratuita quedo con
    # el billing bloqueado (402 Payment required, confirmado real) -- igual
    # que anthropic (issue #17), el codigo del provider se mantiene intacto
    # y vuelve a activarse solo con agregarlo de nuevo a esta lista. anthropic
    # tampoco esta en la lista por defecto. El router solo usa hasta 3
    # providers por request (TaskRouter, principio de gestion de costos).
    provider_priority: str = "gemini,groq,nvidia,opencode,openai"

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
