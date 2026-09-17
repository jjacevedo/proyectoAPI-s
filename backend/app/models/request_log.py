from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    models_used: Mapped[list] = mapped_column(JSONB, nullable=False)
    individual_responses: Mapped[list] = mapped_column(JSONB, nullable=False)
    critiques: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    final_answer: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    complexity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="high")
    disagreement_level: Mapped[str] = mapped_column(String(16), nullable=False, server_default="not_applicable")
    disagreement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    disagreement_evidence: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
