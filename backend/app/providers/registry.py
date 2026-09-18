from app.config import Settings
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.cerebras_provider import CerebrasProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.groq_provider import GroqProvider
from app.providers.nvidia_provider import NvidiaProvider
from app.providers.opencode_provider import OpenCodeProvider
from app.providers.openai_provider import OpenAIProvider


def build_providers(settings: Settings) -> dict[str, LLMProvider]:
    providers: dict[str, LLMProvider] = {}
    if settings.openai_api_key:
        providers["openai"] = OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if settings.anthropic_api_key:
        providers["anthropic"] = AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    if settings.gemini_api_key:
        providers["gemini"] = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    if settings.groq_api_key:
        providers["groq"] = GroqProvider(settings.groq_api_key, settings.groq_model)
    if settings.cerebras_api_key:
        providers["cerebras"] = CerebrasProvider(settings.cerebras_api_key, settings.cerebras_model)
    if settings.nvidia_api_key:
        providers["nvidia"] = NvidiaProvider(settings.nvidia_api_key, settings.nvidia_model)
    if settings.opencode_api_key:
        providers["opencode"] = OpenCodeProvider(settings.opencode_api_key, settings.opencode_model)
    return providers
