from app.providers.base import LLMProvider, LLMResponse


class TestCaseGenerator:
    """Genera UN suite de tests compartido a partir de la solicitud original,
    ANTES de ver ninguna respuesta candidata, para que la verificacion sea
    independiente y no este sesgada hacia ninguna implementacion (seccion 18
    del documento de diseno). Mismo patron que Synthesizer/CrossCritic/
    Reevaluator: arma un prompt y llama a provider.generate().
    """

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    def build_prompt(self, original_prompt: str) -> str:
        return "\n".join([
            "You are writing an independent, objective test suite for a Python "
            "programming request, BEFORE seeing any candidate implementation.",
            "Write ONLY a single `unittest.TestCase` subclass (import unittest, "
            "class Test...(unittest.TestCase): ...) that verifies the behavior "
            "described below, assuming the required function(s)/class(es) "
            "already exist in the global namespace exactly as the request "
            "implies (do not define them yourself, do not include "
            "`if __name__ == \"__main__\"` or a call to unittest.main()).",
            "Keep it deterministic (no randomness, no network, no filesystem, "
            "no timing-dependent assertions) and fast (a few simple cases).",
            "\nREQUEST:\n" + original_prompt,
            "\nReturn only a single Python code block with the test class.",
        ])

    async def run(self, provider: LLMProvider, original_prompt: str) -> LLMResponse:
        prompt = self.build_prompt(original_prompt)
        return await provider.generate(prompt, max_tokens=self.max_tokens)
