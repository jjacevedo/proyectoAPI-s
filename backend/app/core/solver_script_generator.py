from app.providers.base import LLMProvider, LLMResponse


class SolverScriptGenerator:
    """Genera un UNICO script de solucion a partir de la solicitud original,
    ANTES de ver ninguna respuesta candidata, para que la verificacion sea
    independiente y no este sesgada hacia ninguna implementacion (mismo
    principio que TestCaseGenerator para el issue #11). Mismo patron que
    Synthesizer/CrossCritic/Reevaluator/TestCaseGenerator: arma un prompt y
    llama a provider.generate().
    """

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    def build_prompt(self, original_prompt: str) -> str:
        return "\n".join([
            "You are writing an independent, objective calculation script for a "
            "math/arithmetic request, BEFORE seeing any candidate answer.",
            "Write ONLY a short Python script (standard library only — math, "
            "cmath, fractions and decimal are available; no other imports, no "
            "network, no file access) that computes the numeric answer to the "
            "request below and prints EXACTLY one line in this exact format, "
            "with no other output:",
            "__CALC_RESULT__ <number>",
            "The number must be a plain int or float literal representation "
            "(e.g. 42 or 3.14159), not a fraction or expression.",
            "\nREQUEST:\n" + original_prompt,
            "\nReturn only a single Python code block with the script.",
        ])

    async def run(self, provider: LLMProvider, original_prompt: str) -> LLMResponse:
        prompt = self.build_prompt(original_prompt)
        return await provider.generate(prompt, max_tokens=self.max_tokens)
