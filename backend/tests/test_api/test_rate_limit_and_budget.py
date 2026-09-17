import pytest

from app.api.deps import get_db
from app.api.rate_limit_deps import get_rate_limiter
from app.api.routes.chat import get_orchestrator
from app.config import settings
from app.core.orchestrator import DeliberationResult
from app.core.rate_limiter import RateLimiter
from app.core.router import RoutingDecision, TaskComplexity
from app.providers.base import LLMResponse


class FakeOrchestrator:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.LOW, provider_count=1, reason="test")
        return DeliberationResult("final", [response], 12.5, routing)


class FakeSession:
    async def commit(self):
        pass

    def add(self, item):
        pass


async def _fake_db():
    yield FakeSession()


@pytest.mark.asyncio
async def test_rate_limiting_disabled_by_default_allows_many_requests(client, monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "enable_rate_limiting", False)
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_db] = _fake_db

    for _ in range(5):
        response = await client.post("/api/chat", json={"prompt": "hola"})
        assert response.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rate_limiting_enabled_blocks_after_limit(client, monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "enable_rate_limiting", True)
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_db] = _fake_db
    # Una unica instancia reutilizada entre requests: el override debe
    # devolver el MISMO objeto cada vez, igual que el singleton real, para
    # que su estado (hits registrados) persista entre las 3 llamadas.
    test_limiter = RateLimiter(max_requests=2, window_seconds=60)
    app.dependency_overrides[get_rate_limiter] = lambda: test_limiter

    r1 = await client.post("/api/chat", json={"prompt": "hola"})
    r2 = await client.post("/api/chat", json={"prompt": "hola"})
    r3 = await client.post("/api/chat", json={"prompt": "hola"})

    app.dependency_overrides.clear()

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429


@pytest.mark.asyncio
async def test_daily_budget_none_by_default_does_not_block(client, monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "daily_budget_usd", None)
    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/chat", json={"prompt": "hola"})
    app.dependency_overrides.clear()

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_daily_budget_blocks_when_already_spent_today(client, monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "daily_budget_usd", 0.01)

    async def fake_get_spent_today_usd(session):
        return 0.02

    monkeypatch.setattr("app.api.rate_limit_deps.get_spent_today_usd", fake_get_spent_today_usd)

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/chat", json={"prompt": "hola"})
    app.dependency_overrides.clear()

    assert response.status_code == 402


@pytest.mark.asyncio
async def test_daily_budget_allows_when_under_limit(client, monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "daily_budget_usd", 10.0)

    async def fake_get_spent_today_usd(session):
        return 0.5

    monkeypatch.setattr("app.api.rate_limit_deps.get_spent_today_usd", fake_get_spent_today_usd)

    app.dependency_overrides[get_orchestrator] = lambda: FakeOrchestrator()
    app.dependency_overrides[get_db] = _fake_db

    response = await client.post("/api/chat", json={"prompt": "hola"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
