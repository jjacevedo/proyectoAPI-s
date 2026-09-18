from app.config import Settings
from app.providers.cerebras_provider import CerebrasProvider
from app.providers.groq_provider import GroqProvider
from app.providers.nvidia_provider import NvidiaProvider
from app.providers.opencode_provider import OpenCodeProvider
from app.providers.registry import build_providers


def test_default_settings_prefer_free_providers():
    settings = Settings(_env_file=None)
    assert settings.synthesizer_provider == "gemini"
    # cerebras excluido del default: su cuenta gratuita quedo con el billing
    # bloqueado (402 Payment required, confirmado real en produccion) --
    # el provider sigue existiendo en el codigo, solo no esta priorizado.
    assert settings.provider_priority_list == ["gemini", "groq", "nvidia", "opencode", "openai"]
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    # llama-3.3-70b-versatile paso a ser Enterprise-only en Groq (17 jun 2026,
    # confirmado con un 404 model_not_found real) -- el default actual es el
    # que Groq recomienda como reemplazo.
    assert settings.groq_model == "openai/gpt-oss-120b"


def test_build_providers_includes_only_configured_free_providers():
    settings = Settings(
        _env_file=None,
        groq_api_key="groq-key",
        cerebras_api_key="cerebras-key",
        nvidia_api_key="nvidia-key",
        opencode_api_key="opencode-key",
    )
    providers = build_providers(settings)

    assert set(providers.keys()) == {"groq", "cerebras", "nvidia", "opencode"}
    assert isinstance(providers["groq"], GroqProvider)
    assert isinstance(providers["cerebras"], CerebrasProvider)
    assert isinstance(providers["nvidia"], NvidiaProvider)
    assert isinstance(providers["opencode"], OpenCodeProvider)


def test_build_providers_keeps_openai_and_anthropic_available_when_keyed():
    settings = Settings(
        _env_file=None,
        openai_api_key="openai-key",
        anthropic_api_key="anthropic-key",
    )
    providers = build_providers(settings)

    assert set(providers.keys()) == {"openai", "anthropic"}


def test_build_providers_returns_empty_dict_without_any_key():
    settings = Settings(_env_file=None)
    assert build_providers(settings) == {}
