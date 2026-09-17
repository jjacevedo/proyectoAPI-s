"""add critiques column to request_logs

Revision ID: 0003_add_critiques
Revises: 0002_add_complexity
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_add_critiques"
down_revision = "0002_add_complexity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("critiques", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "critiques")
