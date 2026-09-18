from datetime import datetime

from pydantic import BaseModel


class ConversationSummary(BaseModel):
    id: int
    mode: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class MessageListResponse(BaseModel):
    conversation_id: int
    messages: list[MessageResponse]
