from app.core.critic import Critique
from app.providers.base import LLMProvider, LLMResponse


class Reevaluator:
    """Ronda de reevaluacion (seccion 17, "Paso 4" del documento de diseno):
    cada provider revisa su PROPIA respuesta a la luz de las criticas ya
    generadas, antes de la sintesis final. Mismo patron que Synthesizer y
    CrossCritic: arma un prompt y llama a provider.generate().
    """

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    def build_prompt(
        self,
        original_prompt: str,
        own_response: LLMResponse,
        critiques: list[Critique],
    ) -> str:
        parts = [
            "You are revising your own previous answer in a multi-LLM deliberation system.",
            "Other reviewers have since critiqued the candidate answers, including yours.",
            "Read the critiques below and produce an IMPROVED final answer to the original "
            "request: fix any real errors, address valid criticisms, and incorporate missed "
            "points. If a critique is wrong, you may disregard it, but be accurate.",
            "\nORIGINAL REQUEST:\n" + original_prompt,
            f"\nYOUR PREVIOUS ANSWER:\n{own_response.content}",
        ]
        for index, critique in enumerate(critiques, start=1):
            if critique.succeeded:
                parts.append(
                    f"\nCRITIQUE {index} BY {critique.response.provider}/{critique.response.model}:\n"
                    f"{critique.response.content}"
                )
        parts.append("\nReturn only your revised final answer, not a description of the changes.")
        return "\n".join(parts)

    async def run(
        self,
        provider: LLMProvider,
        original_prompt: str,
        own_response: LLMResponse,
        critiques: list[Critique],
    ) -> LLMResponse:
        prompt = self.build_prompt(original_prompt, own_response, critiques)
        return await provider.generate(prompt, max_tokens=self.max_tokens)
