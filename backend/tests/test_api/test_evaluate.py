import pytest

from app.api.deps import get_db
from app.api.routes.evaluate import get_orchestrator
from app.core.orchestrator import DeliberationResult
from app.core.router import RoutingDecision, TaskComplexity
from app.providers.base import LLMProvider, LLMResponse


class FakeProvider(LLMProvider):
    def __init__(self, name: str, responses: list[LLMResponse]):
        self.provider_name = name
        self.model = f"{name}-model"
        self._responses = iter(responses)

    async def generate(self, prompt: str, *, max_tokens: int) -> LLMResponse:
        return next(self._responses)


class FakeSession:
    async def commit(self):
        pass

    def add(self, item):
        pass


async def _fake_db():
    yield FakeSession()


class FakeOrchestratorWithJudgeVerdict:
    def __init__(self):
        self.providers = {
            "fake": FakeProvider(
                "fake",
                [
                    LLMResponse(provider="fake", model="fake-model", content="single answer", tokens=5, cost_estimated_usd=0.001),
                    LLMResponse(
                        provider="fake",
                        model="fake-model",
                        content="The multi-LLM answer is more complete.\n__VERDICT__ multi",
                        tokens=8,
                        cost_estimated_usd=0.002,
                    ),
                ],
            )
        }

    async def run(self, prompt: str) -> DeliberationResult:
        response = LLMResponse(provider="fake", model="fake-model", content="multi answer", tokens=10, cost_estimated_usd=0.01)
        routing = RoutingDecision(complexity=TaskComplexity.LOW, provider_count=1, reason="test")
        return DeliberationResult("multi answer", [response], 50.0, routing)


class FakeOrchestratorWithNoProviders:
    def __init__(self):
        self.providers = {}

    async def run(self, prompt: str) -> DeliberationResult:
        raise AssertionError("should not be called when there are no providers")


@pytest.mark.asyncio
async def test_evaluate_endpoint_returns_comparison_with_judge_verdict(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithJudgeVerdict()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/evaluate", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["single_answer"] == "single answer"
    assert data["single_tokens"] == 5
    assert data["multi_answer"] == "multi answer"
    assert data["multi_tokens"] == 10
    assert data["token_delta"] == 5
    assert data["judge_verdict"] == "multi"
    assert "more complete" in data["judge_reasoning"]
    assert data["judge_error"] is None


@pytest.mark.asyncio
async def test_evaluate_endpoint_returns_502_without_providers(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithNoProviders()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/evaluate", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_evaluate_endpoint_skips_judge_when_disabled(client, monkeypatch):
    from app.api.routes import evaluate as evaluate_module
    from app.main import app

    monkeypatch.setattr(evaluate_module.settings, "enable_evaluation_judge", False)

    class FakeOrchestratorSingleCall:
        def __init__(self):
            self.providers = {
                "fake": FakeProvider(
                    "fake",
                    [LLMResponse(provider="fake", model="fake-model", content="single answer", tokens=5)],
                )
            }

        async def run(self, prompt: str) -> DeliberationResult:
            response = LLMResponse(provider="fake", model="fake-model", content="multi answer", tokens=10)
            routing = RoutingDecision(complexity=TaskComplexity.LOW, provider_count=1, reason="test")
            return DeliberationResult("multi answer", [response], 50.0, routing)

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorSingleCall()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/evaluate", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["judge_verdict"] is None
    assert data["judge_reasoning"] is None
