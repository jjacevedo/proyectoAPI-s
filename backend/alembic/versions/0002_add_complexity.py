"""add complexity column to request_logs

Revision ID: 0002_add_complexity
Revises: 0001_request_logs
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_complexity"
down_revision = "0001_request_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("complexity", sa.String(length=16), nullable=False, server_default="high"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "complexity")
