from app.core.critic import Critique
from app.core.disagreement import DisagreementAssessment, DisagreementLevel
from app.providers.base import LLMProvider, LLMResponse


class Synthesizer:
    def __init__(self, provider: LLMProvider, max_tokens: int) -> None:
        self.provider = provider
        self.max_tokens = max_tokens

    def build_prompt(
        self,
        original_prompt: str,
        responses: list[LLMResponse],
        critiques: list[Critique] | None = None,
        disagreement: DisagreementAssessment | None = None,
    ) -> str:
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
        for critique in critiques or []:
            if critique.succeeded:
                parts.append(
                    f"\nCRITIQUE BY {critique.response.provider}/{critique.response.model} "
                    f"(reviewing {', '.join(critique.reviewed_providers)}):\n{critique.response.content}"
                )
        if critiques:
            parts.append(
                "\nUse the critiques above to catch errors the candidates missed, but weigh "
                "them with the same skepticism as the candidate answers themselves."
            )
        if disagreement and disagreement.level == DisagreementLevel.DISAGREEMENT:
            parts.append(f"\nDISAGREEMENT DETECTED: {disagreement.reason}")
            for item in disagreement.evidence:
                parts.append(f"- {item}")
            parts.append(
                "\nResolve this disagreement explicitly in your final answer: state which "
                "position is more likely correct and why, or acknowledge the uncertainty if "
                "you cannot determine it."
            )
        parts.append("\nReturn only the final user-facing answer.")
        return "\n".join(parts)

    async def run(
        self,
        original_prompt: str,
        responses: list[LLMResponse],
        critiques: list[Critique] | None = None,
        disagreement: DisagreementAssessment | None = None,
    ) -> LLMResponse:
        prompt = self.build_prompt(original_prompt, responses, critiques, disagreement)
        return await self.provider.generate(prompt, max_tokens=self.max_tokens)
