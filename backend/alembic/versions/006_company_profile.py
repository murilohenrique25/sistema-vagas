"""expand employer company profile"""

from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, length in (
        ("legal_name", 255), ("email", 255), ("phone", 30),
        ("industry", 120), ("company_size", 30), ("city", 120),
        ("state", 2), ("address", 500), ("logo_url", 500),
    ):
        op.add_column("companies", sa.Column(name, sa.String(length), nullable=True))
    op.add_column("companies", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_companies_owner_id", "companies", ["owner_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_companies_owner_id", table_name="companies")
    for name in ("updated_at", "logo_url", "address", "state", "city", "company_size", "industry", "phone", "email", "legal_name"):
        op.drop_column("companies", name)
