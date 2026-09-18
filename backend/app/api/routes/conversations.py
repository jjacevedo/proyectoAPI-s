from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.message import Message
from app.schemas.conversation import (
    ConversationListResponse,
    ConversationSummary,
    MessageListResponse,
    MessageResponse,
)
from app.services.conversation_service import (
    delete_conversation,
    get_conversation,
    list_conversations,
    list_messages,
)

router = APIRouter(tags=["conversations"])

_TITLE_MAX_LENGTH = 60
_EMPTY_CONVERSATION_TITLE = "Conversación vacía"


def _derive_title(first_message: Message | None) -> str:
    if first_message is None:
        return _EMPTY_CONVERSATION_TITLE
    content = first_message.content.strip()
    if len(content) <= _TITLE_MAX_LENGTH:
        return content
    return f"{content[:_TITLE_MAX_LENGTH].rstrip()}…"


@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(db: AsyncSession = Depends(get_db)) -> ConversationListResponse:
    rows = await list_conversations(db)
    summaries = [
        ConversationSummary(
            id=conversation.id,
            mode=conversation.mode,
            title=_derive_title(first_message),
            created_at=conversation.created_at,
            updated_at=last_message.created_at if last_message else conversation.created_at,
        )
        for conversation, first_message, last_message in rows
    ]
    return ConversationListResponse(conversations=summaries)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def get_conversation_messages(conversation_id: int, db: AsyncSession = Depends(get_db)) -> MessageListResponse:
    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await list_messages(db, conversation_id)
    return MessageListResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(id=message.id, role=message.role, content=message.content, created_at=message.created_at)
            for message in messages
        ],
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def remove_conversation(conversation_id: int, db: AsyncSession = Depends(get_db)) -> None:
    deleted = await delete_conversation(db, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
