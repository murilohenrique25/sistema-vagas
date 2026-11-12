"""company CNPJ verification metadata

Revision ID: 011
Revises: 010
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("cnpj_status", sa.String(50), nullable=True))
    op.add_column("companies", sa.Column("cnpj_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("companies", sa.Column("cnpj_source", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "cnpj_source")
    op.drop_column("companies", "cnpj_checked_at")
    op.drop_column("companies", "cnpj_status")
