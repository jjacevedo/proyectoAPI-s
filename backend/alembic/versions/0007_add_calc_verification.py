"""add calculation verification columns to request_logs

Revision ID: 0007_add_calc_verification
Revises: 0006_add_code_verification
Create Date: 2026-09-17

Nota: el id de revision se abrevio a "calc_verification" (en vez de
"calculation_verification") porque alembic_version.version_num es
VARCHAR(32) por defecto y el nombre completo lo excedia — un fallo real
detectado corriendo la migracion contra PostgreSQL real, no supuesto.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_add_calc_verification"
down_revision = "0006_add_code_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "request_logs",
        sa.Column("reference_calculation", sa.Text(), nullable=True),
    )
    op.add_column(
        "request_logs",
        sa.Column("calculation_verifications", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("request_logs", "calculation_verifications")
    op.drop_column("request_logs", "reference_calculation")
