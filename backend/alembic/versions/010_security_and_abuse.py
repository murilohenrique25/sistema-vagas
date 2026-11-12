"""session revocation and job reports

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa

revision="010"; down_revision="009"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column("users", sa.Column("session_version", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("totp_secret", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_table("job_reports", sa.Column("id",sa.UUID(),primary_key=True),sa.Column("job_id",sa.UUID(),sa.ForeignKey("jobs.id",ondelete="CASCADE"),nullable=False),sa.Column("reporter_id",sa.UUID(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("reason",sa.String(50),nullable=False),sa.Column("details",sa.String(1000)),sa.Column("status",sa.String(20),server_default="pending",nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),sa.UniqueConstraint("job_id","reporter_id",name="uq_job_reporter"))
    op.create_index("ix_job_reports_status","job_reports",["status"])
def downgrade():
    op.drop_table("job_reports"); op.drop_column("users","totp_enabled"); op.drop_column("users","totp_secret"); op.drop_column("users","session_version")
