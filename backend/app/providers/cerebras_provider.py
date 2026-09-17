from app.providers.openai_compatible_provider import OpenAICompatibleProvider

CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"


class CerebrasProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model, base_url=CEREBRAS_BASE_URL, provider_name="cerebras")
