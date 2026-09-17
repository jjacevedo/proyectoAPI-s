from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


# USD / 1M tokens. Keep this table easy to update as providers change prices.
PRICING: dict[str, ModelPricing] = {
    "gpt-5.6-luna": ModelPricing(0.20, 1.20),
    "gpt-5.6-terra": ModelPricing(2.00, 12.00),
    "gpt-5.6-sol": ModelPricing(4.00, 20.00),
    "gpt-5.6": ModelPricing(4.00, 20.00),
    "claude-sonnet-5": ModelPricing(2.00, 10.00),
    "claude-opus-5": ModelPricing(5.00, 25.00),
    "claude-haiku-4-5-20251001": ModelPricing(1.00, 5.00),
    "gemini-3.8-flash": ModelPricing(0.75, 3.75),
    "gemini-3.7-flash": ModelPricing(0.75, 3.75),
    "gemini-3.6-flash": ModelPricing(0.75, 3.75),
    "gemini-3.5-flash": ModelPricing(1.50, 9.00),
    "gemini-3.5-flash-lite": ModelPricing(0.30, 2.50),

    # Defaults gratuitos (Groq/Cerebras/Google AI Studio free tier). $0/$0 para
    # que la UI muestre un costo real de $0 en vez de "N/D" con estos modelos.
    "gemini-3.1-flash-lite": ModelPricing(0.0, 0.0),
    # "llama-3.3-70b-versatile" quedo en el free tier de Groq hasta que Groq lo
    # movio a Enterprise-only (17 jun 2026); se deja el precio $0 por si se
    # reactiva a mano con otra cuenta, pero ya no es el default de GROQ_MODEL.
    "llama-3.3-70b-versatile": ModelPricing(0.0, 0.0),
    "gpt-oss-120b": ModelPricing(0.0, 0.0),
    # Mismo modelo open-weight que "gpt-oss-120b", pero con el prefijo que usa
    # Groq en su catalogo (GROQ_MODEL, tras la deprecacion de Llama 3.3 70B).
    "openai/gpt-oss-120b": ModelPricing(0.0, 0.0),
    # NVIDIA NIM (build.nvidia.com): tier de desarrollador gratuito.
    "meta/llama-3.1-70b-instruct": ModelPricing(0.0, 0.0),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    return (
        input_tokens * pricing.input_per_million / 1_000_000
        + output_tokens * pricing.output_per_million / 1_000_000
    )
