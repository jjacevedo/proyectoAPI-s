"""add task_type and code verification columns to request_logs

Revision ID: 0006_add_code_verification
Revises: 0005_add_revisions
Create Date: 2026-09-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_add_code_verification"
down_revision = "0005_add_revisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("task_type", sa.String(length=16), nullable=False, server_default="general"),
    )
    op.add_column(
        "request_logs",
        sa.Column("generated_tests", sa.Text(), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("code_verifications", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "code_verifications")
    op.drop_column("request_logs", "generated_tests")
    op.drop_column("request_logs", "task_type")
