from app.providers.openai_compatible_provider import OpenAICompatibleProvider

OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"


class OpenCodeProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model, base_url=OPENCODE_BASE_URL, provider_name="opencode")
