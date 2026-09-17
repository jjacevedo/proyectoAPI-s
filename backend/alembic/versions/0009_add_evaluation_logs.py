"""create evaluation_logs table

Revision ID: 0009_add_evaluation_logs
Revises: 0008_add_fact_search
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_add_evaluation_logs"
down_revision = "0008_add_fact_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("single_provider", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("single_model", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("single_answer", sa.Text(), nullable=True),
        sa.Column("single_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("single_cost_usd", sa.Float(), nullable=True),
        sa.Column("single_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("single_error", sa.Text(), nullable=True),
        sa.Column("multi_answer", sa.Text(), nullable=False),
        sa.Column("multi_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("multi_cost_usd", sa.Float(), nullable=True),
        sa.Column("multi_latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("judge_verdict", sa.String(length=16), nullable=True),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column("judge_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_logs")
