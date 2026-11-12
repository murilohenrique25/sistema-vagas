"""add direct service payment tracking"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("payments", sa.Column("purpose", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("payments", sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_payments_purpose_resource", "payments", ["purpose", "resource_id"])

def downgrade() -> None:
    op.drop_index("ix_payments_purpose_resource", table_name="payments")
    op.drop_column("payments", "consumed_at")
    op.drop_column("payments", "resource_id")
    op.drop_column("payments", "purpose")
