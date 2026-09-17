from unittest.mock import AsyncMock

import pytest

from app.api.routes.chat import get_orchestrator
from app.core.orchestrator import DeliberationResult
from app.providers.base import LLMResponse


class FakeOrchestrator:
    async def run(self, prompt: str):
        response = LLMResponse(provider="openai", model="test", content="final", tokens=4)
        return DeliberationResult("final", [response], 12.5)


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
