import pytest

from app.api.deps import get_db
from app.api.routes.chat import get_mode_orchestrator_builder, get_orchestrator
from app.core.orchestrator import DeliberationResult
from app.core.router import RoutingDecision, TaskComplexity
from app.models.conversation import Conversation
from app.models.message import Message
from app.providers.base import LLMResponse


class FakeOrchestrator:
    def __init__(self, answer: str = "final"):
        self.answer = answer
        self.received_prompts: list[str] = []

    async def run(self, prompt: str):
        self.received_prompts.append(prompt)
        response = LLMResponse(provider="openai", model="test", content=self.answer, tokens=4)
        routing = RoutingDecision(complexity=TaskComplexity.LOW, provider_count=1, reason="test")
        return DeliberationResult(self.answer, [response], 12.5, routing)


class FakeScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalars(self._items)


class FakeSession:
    """Sesion falsa que soporta lo minimo que necesita conversation_service:
    add/commit/refresh (creacion), get (lookup por id), execute (historial)."""

    def __init__(self, existing_conversation: Conversation | None = None, history: list[Message] | None = None):
        self._next_id = 1
        self._existing_conversation = existing_conversation
        self._history = history or []
        self.added_messages: list[Message] = []

    def add(self, item):
        if isinstance(item, Message):
            self.added_messages.append(item)

    async def commit(self):
        pass

    async def refresh(self, item):
        item.id = self._next_id
        self._next_id += 1

    async def get(self, model, item_id):
        if self._existing_conversation is not None and item_id == self._existing_conversation.id:
            return self._existing_conversation
        return None

    async def execute(self, query):
        return FakeResult(self._history)


@pytest.mark.asyncio
async def test_chat_without_conversation_fields_is_unaffected(client):
    from app.main import app

    fake_orchestrator = FakeOrchestrator()

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    app.dependency_overrides[get_db] = fake_db

    response = await client.post("/api/chat", json={"prompt": "hola"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] is None
    assert fake_orchestrator.received_prompts == ["hola"]


@pytest.mark.asyncio
async def test_chat_with_mode_creates_conversation_and_returns_id(client):
    from app.main import app

    fake_orchestrator = FakeOrchestrator()
    fake_session = FakeSession()

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    app.dependency_overrides[get_mode_orchestrator_builder] = lambda: (lambda mode: fake_orchestrator)
    app.dependency_overrides[get_db] = fake_db

    response = await client.post("/api/chat", json={"prompt": "hola", "mode": "fast"})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == 1
    assert len(fake_session.added_messages) == 2
    assert fake_session.added_messages[0].role == "user"
    assert fake_session.added_messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_chat_with_existing_conversation_includes_history_in_prompt(client):
    from app.main import app

    conversation = Conversation(mode="deliberation")
    conversation.id = 42
    history = [
        Message(conversation_id=42, role="user", content="¿Qué es Python?"),
        Message(conversation_id=42, role="assistant", content="Un lenguaje de programación."),
    ]
    fake_orchestrator = FakeOrchestrator()
    fake_session = FakeSession(existing_conversation=conversation, history=history)

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    app.dependency_overrides[get_db] = fake_db

    response = await client.post("/api/chat", json={"prompt": "¿Y JavaScript?", "conversation_id": 42})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == 42
    assert len(fake_orchestrator.received_prompts) == 1
    sent_prompt = fake_orchestrator.received_prompts[0]
    assert "¿Qué es Python?" in sent_prompt
    assert "¿Y JavaScript?" in sent_prompt


@pytest.mark.asyncio
async def test_chat_with_unknown_conversation_id_returns_404(client):
    from app.main import app

    fake_orchestrator = FakeOrchestrator()
    fake_session = FakeSession(existing_conversation=None)

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_orchestrator] = lambda: fake_orchestrator
    app.dependency_overrides[get_db] = fake_db

    response = await client.post("/api/chat", json={"prompt": "hola", "conversation_id": 999})
    app.dependency_overrides.clear()

    assert response.status_code == 404
