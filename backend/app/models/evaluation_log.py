from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    single_provider: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")
    single_model: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    single_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    single_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    single_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    single_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    single_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    multi_answer: Mapped[str] = mapped_column(Text, nullable=False)
    multi_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    multi_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    multi_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    judge_verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    judge_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
