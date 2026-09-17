"""add fact search results column to request_logs

Revision ID: 0008_add_fact_search
Revises: 0007_add_calc_verification
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_add_fact_search"
down_revision = "0007_add_calc_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("fact_search_results", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "fact_search_results")
