from datetime import datetime, timedelta, timezone

import pytest

from app.api.deps import get_db
from app.models.conversation import Conversation
from app.models.message import Message

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


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
    """Sesion falsa para las rutas de conversaciones: mantiene listas mutables
    de conversaciones/mensajes en memoria, y despacha select/delete segun la
    entidad objetivo (Conversation vs Message) y el valor del parametro
    ligado (escalar para filtro por igualdad, lista para IN(...))."""

    def __init__(self, conversations=None, messages=None):
        self.conversations: list[Conversation] = list(conversations or [])
        self.messages: list[Message] = list(messages or [])

    async def get(self, model, item_id):
        if model is Conversation:
            return next((c for c in self.conversations if c.id == item_id), None)
        return None

    async def delete(self, item):
        self.conversations = [c for c in self.conversations if c.id != item.id]

    async def commit(self):
        pass

    async def execute(self, query):
        params = query.compile().params
        value = next(iter(params.values()), None)

        if getattr(query, "is_delete", False):
            self.messages = [m for m in self.messages if m.conversation_id != value]
            return FakeResult([])

        entity = query.column_descriptions[0]["entity"]
        if entity is Conversation:
            return FakeResult(sorted(self.conversations, key=lambda c: c.id, reverse=True))

        if isinstance(value, (list, tuple, set)):
            matched = [m for m in self.messages if m.conversation_id in value]
        elif value is not None:
            matched = [m for m in self.messages if m.conversation_id == value]
        else:
            matched = list(self.messages)
        return FakeResult(sorted(matched, key=lambda m: m.id))


def _conversation(conversation_id: int, mode: str = "deliberation") -> Conversation:
    conversation = Conversation(mode=mode)
    conversation.id = conversation_id
    conversation.created_at = _BASE_TIME + timedelta(minutes=conversation_id)
    return conversation


def _message(message_id: int, conversation_id: int, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    message.id = message_id
    message.created_at = _BASE_TIME + timedelta(minutes=conversation_id, seconds=message_id)
    return message


@pytest.mark.asyncio
async def test_list_conversations_empty(client):
    from app.main import app

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/conversations")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"conversations": []}


@pytest.mark.asyncio
async def test_list_conversations_returns_title_and_order(client):
    from app.main import app

    conversations = [_conversation(1), _conversation(2)]
    messages = [
        _message(1, 1, "user", "¿Qué es Python?"),
        _message(2, 1, "assistant", "Un lenguaje de programación."),
        _message(3, 2, "user", "Explica el patrón greedy"),
        _message(4, 2, "assistant", "Un algoritmo greedy elige la opción óptima local."),
    ]
    fake_session = FakeSession(conversations=conversations, messages=messages)

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/conversations")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["conversations"]
    assert [c["id"] for c in data] == [2, 1]
    assert data[0]["title"] == "Explica el patrón greedy"
    assert data[1]["title"] == "¿Qué es Python?"


@pytest.mark.asyncio
async def test_list_conversations_with_no_messages_uses_fallback_title(client):
    from app.main import app

    conversation = _conversation(5)

    async def fake_db():
        yield FakeSession(conversations=[conversation])

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/conversations")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["conversations"]
    assert data[0]["title"] == "Conversación vacía"


@pytest.mark.asyncio
async def test_get_messages_for_existing_conversation(client):
    from app.main import app

    conversation = _conversation(7)
    messages = [
        _message(1, 7, "user", "hola"),
        _message(2, 7, "assistant", "¿en qué te ayudo?"),
    ]

    async def fake_db():
        yield FakeSession(conversations=[conversation], messages=messages)

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/conversations/7/messages")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == 7
    assert [m["role"] for m in data["messages"]] == ["user", "assistant"]
    assert [m["content"] for m in data["messages"]] == ["hola", "¿en qué te ayudo?"]


@pytest.mark.asyncio
async def test_get_messages_for_missing_conversation_returns_404(client):
    from app.main import app

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.get("/api/conversations/999/messages")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


@pytest.mark.asyncio
async def test_delete_existing_conversation_returns_204(client):
    from app.main import app

    conversation = _conversation(3)
    messages = [_message(1, 3, "user", "hola")]
    fake_session = FakeSession(conversations=[conversation], messages=messages)

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_db] = fake_db
    response = await client.delete("/api/conversations/3")
    app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_missing_conversation_returns_404(client):
    from app.main import app

    async def fake_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = fake_db
    response = await client.delete("/api/conversations/999")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


@pytest.mark.asyncio
async def test_deleted_conversation_messages_are_also_gone(client):
    from app.main import app

    conversation = _conversation(9)
    messages = [_message(1, 9, "user", "hola"), _message(2, 9, "assistant", "hola de vuelta")]
    fake_session = FakeSession(conversations=[conversation], messages=messages)

    async def fake_db():
        yield fake_session

    app.dependency_overrides[get_db] = fake_db
    delete_response = await client.delete("/api/conversations/9")
    messages_response = await client.get("/api/conversations/9/messages")
    app.dependency_overrides.clear()

    assert delete_response.status_code == 204
    assert messages_response.status_code == 404
    assert fake_session.messages == []
