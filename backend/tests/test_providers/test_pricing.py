from app.providers.pricing import estimate_cost


def test_free_tier_default_models_cost_zero():
    assert estimate_cost("gpt-oss-120b", 1000, 1000) == 0.0
    assert estimate_cost("openai/gpt-oss-120b", 1000, 1000) == 0.0
    assert estimate_cost("llama-3.3-70b-versatile", 1000, 1000) == 0.0
    assert estimate_cost("gemini-3.1-flash-lite", 1000, 1000) == 0.0
    assert estimate_cost("meta/llama-3.1-70b-instruct", 1000, 1000) == 0.0
    assert estimate_cost("meta/llama-3.3-70b-instruct", 1000, 1000) == 0.0
    assert estimate_cost("meta/llama-4-scout-17b-16e-instruct", 1000, 1000) == 0.0
    assert estimate_cost("meta/llama-4-maverick-17b-128e-instruct", 1000, 1000) == 0.0
    assert estimate_cost("big-pickle", 1000, 1000) == 0.0


def test_unrecognized_model_returns_none():
    assert estimate_cost("some-unconfigured-model", 1, 1) is None


def test_paid_model_still_priced():
    assert estimate_cost("gpt-5.6-luna", 1_000_000, 0) == 0.20
