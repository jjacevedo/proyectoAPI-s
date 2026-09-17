"""add disagreement columns to request_logs

Revision ID: 0004_add_disagreement
Revises: 0003_add_critiques
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_add_disagreement"
down_revision = "0003_add_critiques"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("disagreement_level", sa.String(length=16), nullable=False, server_default="not_applicable"),
    )
    op.add_column(
        "request_logs",
        sa.Column("disagreement_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("disagreement_evidence", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "disagreement_evidence")
    op.drop_column("request_logs", "disagreement_reason")
    op.drop_column("request_logs", "disagreement_level")
