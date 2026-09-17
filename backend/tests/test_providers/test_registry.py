from app.config import Settings
from app.providers.cerebras_provider import CerebrasProvider
from app.providers.groq_provider import GroqProvider
from app.providers.registry import build_providers


def test_default_settings_prefer_free_providers():
    settings = Settings(_env_file=None)
    assert settings.synthesizer_provider == "cerebras"
    assert settings.provider_priority_list == ["cerebras", "gemini", "groq", "openai"]
    assert settings.gemini_model == "gemini-3.1-flash-lite"


def test_build_providers_includes_only_configured_free_providers():
    settings = Settings(
        _env_file=None,
        groq_api_key="groq-key",
        cerebras_api_key="cerebras-key",
    )
    providers = build_providers(settings)

    assert set(providers.keys()) == {"groq", "cerebras"}
    assert isinstance(providers["groq"], GroqProvider)
    assert isinstance(providers["cerebras"], CerebrasProvider)


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
