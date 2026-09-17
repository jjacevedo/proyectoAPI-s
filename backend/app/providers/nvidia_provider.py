from app.providers.openai_compatible_provider import OpenAICompatibleProvider

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(api_key, model, base_url=NVIDIA_BASE_URL, provider_name="nvidia")
