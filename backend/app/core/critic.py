from pydantic import BaseModel, ConfigDict

from app.providers.base import LLMProvider, LLMResponse


class Critique(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    response: LLMResponse
    reviewed_providers: list[str]

    @property
    def succeeded(self) -> bool:
        return self.response.succeeded


class CrossCritic:
    """Construye un prompt de critica cruzada y lo ejecuta via
    provider.generate(), siguiendo el mismo patron que Synthesizer: la
    logica vive aqui, no en un metodo especial del provider.
    """

    def __init__(self, max_tokens: int) -> None:
        self.max_tokens = max_tokens

    def build_prompt(
        self,
        original_prompt: str,
        own_response: LLMResponse,
        other_responses: list[LLMResponse],
    ) -> str:
        parts = [
            "You are acting as a critical reviewer in a multi-LLM deliberation system.",
            "You already produced your own answer to the request below. Review only the "
            "OTHER candidate answers listed below — do not critique your own answer.",
            "For each of the other candidate answers, identify explicitly:",
            "- Errores factuales o de razonamiento",
            "- Contradicciones (con la evidencia o entre las respuestas)",
            "- Supuestos no justificados",
            "- Omisiones relevantes",
            "- Ventajas o aciertos",
            "- Limitaciones",
            "- Mejoras posibles",
            "Be specific and reference which candidate you are discussing by its label.",
            "\nORIGINAL REQUEST:\n" + original_prompt,
            f"\nYOUR OWN ANSWER ({own_response.provider}/{own_response.model}), for context only, do not critique it:\n{own_response.content}",
        ]
        for index, response in enumerate(other_responses, start=1):
            parts.append(
                f"\nCANDIDATE {index} ({response.provider}/{response.model}):\n{response.content}"
            )
        parts.append("\nReturn only your critique, organized by candidate.")
        return "\n".join(parts)

    async def run(
        self,
        provider: LLMProvider,
        original_prompt: str,
        own_response: LLMResponse,
        other_responses: list[LLMResponse],
    ) -> Critique:
        prompt = self.build_prompt(original_prompt, own_response, other_responses)
        result = await provider.generate(prompt, max_tokens=self.max_tokens)
        return Critique(
            response=result,
            reviewed_providers=[f"{r.provider}/{r.model}" for r in other_responses],
        )
