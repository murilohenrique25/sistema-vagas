"""add BRL wallet balance"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("users", sa.Column("wallet_balance", sa.Numeric(12, 2), server_default="0", nullable=False))

def downgrade() -> None:
    op.drop_column("users", "wallet_balance")
