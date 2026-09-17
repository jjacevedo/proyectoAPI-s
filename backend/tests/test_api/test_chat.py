from unittest.mock import AsyncMock

import pytest

from app.api.routes.chat import get_orchestrator
from app.core.calculation_verifier import CalculationVerification
from app.core.code_verifier import CodeVerification
from app.core.critic import Critique
from app.core.fact_search import FactCheckResult
from app.core.disagreement import DisagreementAssessment, DisagreementLevel
from app.core.orchestrator import DeliberationResult
from app.core.router import RoutingDecision, TaskComplexity, TaskType
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


class FakeOrchestratorWithRevisions:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.HIGH, provider_count=2, reason="test")
        revision = LLMResponse(provider="openai", model="test", content="revised final", tokens=5)
        return DeliberationResult("final", [response], 12.5, routing, revisions=[revision])


class FakeOrchestratorWithCodeVerification:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(
            complexity=TaskComplexity.MEDIUM, provider_count=2, reason="test", task_type=TaskType.CODE
        )
        test_generation = LLMResponse(provider="openai", model="test", content="```python\nclass T: pass\n```", tokens=6)
        verification = CodeVerification(
            provider="openai",
            model="test",
            passed=True,
            tests_run=1,
            tests_passed=1,
            tests_failed=0,
            stdout="ok",
            stderr="",
        )
        return DeliberationResult(
            "final",
            [response],
            12.5,
            routing,
            code_verifications=[verification],
            generated_tests="class T: pass",
            test_generation=test_generation,
        )


class FakeOrchestratorWithCalculationVerification:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(
            complexity=TaskComplexity.MEDIUM, provider_count=2, reason="test", task_type=TaskType.MATH
        )
        solver_generation = LLMResponse(
            provider="openai", model="test", content="```python\nprint('__CALC_RESULT__ 240')\n```", tokens=7
        )
        verification = CalculationVerification(
            provider="openai",
            model="test",
            passed=True,
            candidate_value=240.0,
            reference_value=240.0,
            difference=0.0,
        )
        return DeliberationResult(
            "final",
            [response],
            12.5,
            routing,
            calculation_verifications=[verification],
            reference_calculation="print('__CALC_RESULT__ 240')",
            solver_generation=solver_generation,
        )


class FakeOrchestratorWithFactSearch:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(
            complexity=TaskComplexity.LOW, provider_count=1, reason="test", task_type=TaskType.FACTUAL
        )
        fact_query_generation = LLMResponse(
            provider="openai", model="test", content="Alan Turing nacimiento", tokens=6
        )
        fact_result = FactCheckResult(
            query="Alan Turing nacimiento",
            title="Alan Turing",
            extract="Alan Turing nació el 23 de junio de 1912.",
            url="https://es.wikipedia.org/wiki/Alan_Turing",
        )
        return DeliberationResult(
            "final",
            [response],
            12.5,
            routing,
            fact_search_results=[fact_result],
            fact_query_generation=fact_query_generation,
        )


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
    assert data["revisions"] == []
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


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_revisions(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithRevisions()
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
    assert len(data["revisions"]) == 1
    assert data["revisions"][0]["content"] == "revised final"
    assert data["total_tokens"] == 4 + 5


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_code_verification(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithCodeVerification()
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
    assert data["task_type"] == "code"
    assert data["generated_tests"] == "class T: pass"
    assert len(data["code_verifications"]) == 1
    assert data["code_verifications"][0]["provider"] == "openai"
    assert data["code_verifications"][0]["passed"] is True
    assert data["total_tokens"] == 4 + 6


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_calculation_verification(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithCalculationVerification()
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
    assert data["task_type"] == "math"
    assert data["reference_calculation"] == "print('__CALC_RESULT__ 240')"
    assert len(data["calculation_verifications"]) == 1
    assert data["calculation_verifications"][0]["provider"] == "openai"
    assert data["calculation_verifications"][0]["passed"] is True
    assert data["calculation_verifications"][0]["reference_value"] == 240.0
    assert data["total_tokens"] == 4 + 7


@pytest.mark.asyncio
async def test_chat_endpoint_exposes_fact_search(client):
    from app.main import app

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestratorWithFactSearch()
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
    assert data["task_type"] == "factual"
    assert len(data["fact_search_results"]) == 1
    assert data["fact_search_results"][0]["query"] == "Alan Turing nacimiento"
    assert data["fact_search_results"][0]["extract"] == "Alan Turing nació el 23 de junio de 1912."
    assert data["total_tokens"] == 4 + 6
