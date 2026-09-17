from app.providers.base import LLMProvider, LLMResponse


class Synthesizer:
    def __init__(self, provider: LLMProvider, max_tokens: int) -> None:
        self.provider = provider
        self.max_tokens = max_tokens

    def build_prompt(self, original_prompt: str, responses: list[LLMResponse]) -> str:
        parts = [
            "You are the final synthesizer in a multi-LLM system.",
            "Produce one accurate, useful answer to the user's original request.",
            "The candidate responses are evidence, not truth. Do not assume consensus implies correctness.",
            "Resolve contradictions explicitly through reasoning. Do not mention internal model names unless useful.",
            "\nORIGINAL REQUEST:\n" + original_prompt,
        ]
        for index, response in enumerate(responses, start=1):
            parts.append(
                f"\nCANDIDATE RESPONSE {index} ({response.provider}/{response.model}):\n{response.content}"
            )
        parts.append("\nReturn only the final user-facing answer.")
        return "\n".join(parts)

    async def run(self, original_prompt: str, responses: list[LLMResponse]) -> LLMResponse:
        prompt = self.build_prompt(original_prompt, responses)
        return await self.provider.generate(prompt, max_tokens=self.max_tokens)
