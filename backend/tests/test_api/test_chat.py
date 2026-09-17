from unittest.mock import AsyncMock

import pytest

from app.api.routes.chat import get_orchestrator
from app.core.critic import Critique
from app.core.disagreement import DisagreementAssessment, DisagreementLevel
from app.core.orchestrator import DeliberationResult
from app.core.router import RoutingDecision, TaskComplexity
from app.providers.base import LLMResponse


class FakeOrchestrator:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.LOW, provider_count=1, reason="test")
        return DeliberationResult("final", [response], 12.5, routing)


class FakeOrchestratorWithCritique:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.HIGH, provider_count=2, reason="test")
        critique = Critique(
            response=LLMResponse(provider="anthropic", model="test2", content="crit", tokens=3),
            reviewed_providers=["openai/test"],
        )
        return DeliberationResult("final", [response], 12.5, routing, critiques=[critique])


class FakeOrchestratorWithDisagreement:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.HIGH, provider_count=2, reason="test")
        disagreement = DisagreementAssessment(
            level=DisagreementLevel.DISAGREEMENT,
            reason="contradiction found",
            evidence=["candidate 2 contradice al candidate 1"],
        )
        return DeliberationResult("final", [response], 12.5, routing, disagreement=disagreement)


@pytest.mark.asyncio
async def test_chat_endpoint(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    # The persistence dependency is replaced with a lightweight fake session.
    from app.api.deps import get_db

    class FakeSession:
        async def commit(self):
            pass

        def add(self, item):
            pass

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.post("/api/chat", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["final_answer"] == "final"
    assert data["responses"][0]["provider"] == "openai"
    assert data["critiques"] == []
    assert data["disagreement_level"] == "not_applicable"


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_critiques(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithCritique()
    from app.api.deps import get_db

    class FakeSession:
        async def commit(self):
            pass

        def add(self, item):
            pass

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.post("/api/chat", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert len(data["critiques"]) == 1
    assert data["critiques"][0]["provider"] == "anthropic"
    assert data["critiques"][0]["reviewed_providers"] == ["openai/test"]
    assert data["total_tokens"] == 4 + 3


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_disagreement(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithDisagreement()
    from app.api.deps import get_db

    class FakeSession:
        async def commit(self):
            pass

        def add(self, item):
            pass

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.post("/api/chat", json={"prompt": "hello"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["disagreement_level"] == "disagreement"
    assert data["disagreement_reason"] == "contradiction found"
    assert data["disagreement_evidence"] == ["candidate 2 contradice al candidate 1"]
