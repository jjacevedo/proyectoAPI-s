from app.providers.openai_compatible_provider import OpenAICompatibleProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model, base_url=GROQ_BASE_URL, provider_name="groq")
