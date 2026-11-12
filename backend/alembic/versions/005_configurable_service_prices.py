"""configurable service prices

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_settings",
        sa.Column("job_posting_price", sa.Numeric(12, 2), nullable=False, server_default="10.00"),
    )
    op.add_column(
        "payment_settings",
        sa.Column("resume_analysis_price", sa.Numeric(12, 2), nullable=False, server_default="5.00"),
    )
    op.add_column(
        "payment_settings",
        sa.Column("job_compatibility_price", sa.Numeric(12, 2), nullable=False, server_default="5.00"),
    )
    op.add_column(
        "payment_settings",
        sa.Column("minimum_wallet_topup", sa.Numeric(12, 2), nullable=False, server_default="1.00"),
    )
    op.create_check_constraint(
        "ck_payment_settings_positive_prices",
        "payment_settings",
        "job_posting_price > 0 AND resume_analysis_price > 0 AND "
        "job_compatibility_price > 0 AND minimum_wallet_topup > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payment_settings_positive_prices", "payment_settings", type_="check")
    op.drop_column("payment_settings", "minimum_wallet_topup")
    op.drop_column("payment_settings", "job_compatibility_price")
    op.drop_column("payment_settings", "resume_analysis_price")
    op.drop_column("payment_settings", "job_posting_price")
