from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message

VALID_MODES = ("fast", "deliberation", "max_verification")


async def create_conversation(session: AsyncSession, mode: str) -> Conversation:
    conversation = Conversation(mode=mode)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def get_conversation(session: AsyncSession, conversation_id: int) -> Conversation | None:
    return await session.get(Conversation, conversation_id)


async def get_recent_messages(session: AsyncSession, conversation_id: int, limit: int) -> list[Message]:
    result = await session.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id.desc()).limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def append_message(session: AsyncSession, conversation_id: int, role: str, content: str) -> None:
    session.add(Message(conversation_id=conversation_id, role=role, content=content))
    await session.commit()


def build_contextual_prompt(history: list[Message], new_prompt: str) -> str:
    if not history:
        return new_prompt
    lines = ["Historial de la conversación (más reciente al final):"]
    for message in history:
        speaker = "Usuario" if message.role == "user" else "Asistente"
        lines.append(f"{speaker}: {message.content}")
    lines.append("")
    lines.append(f"Nuevo mensaje del usuario: {new_prompt}")
    return "\n".join(lines)
