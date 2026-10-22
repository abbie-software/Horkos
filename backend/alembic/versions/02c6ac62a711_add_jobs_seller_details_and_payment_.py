"""add jobs, seller details and payment details

Revision ID: 02c6ac62a711
Revises: de8f846b8465
Create Date: 2026-10-22 14:15:28.437665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02c6ac62a711'
down_revision: Union[str, Sequence[str], None] = 'de8f846b8465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Add the jobs table, seller slugs and counters, and the payment details."""
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("acceptance_tests_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_seller_id"), "jobs", ["seller_id"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)

    with op.batch_alter_table("sellers") as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=40), nullable=True))
        batch_op.add_column(
            sa.Column("jobs_completed", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("jobs_failed", sa.Integer(), server_default="0", nullable=False)
        )
        batch_op.add_column(
            sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_index("ix_sellers_slug", ["slug"], unique=True)

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("job_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("decision_json", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("payout_ref", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("refund_ref", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_payments_job_id", ["job_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_index("ix_payments_job_id")
        batch_op.drop_column("refund_ref")
        batch_op.drop_column("payout_ref")
        batch_op.drop_column("decision_json")
        batch_op.drop_column("job_id")

    with op.batch_alter_table("sellers") as batch_op:
        batch_op.drop_index("ix_sellers_slug")
        batch_op.drop_column("last_activity_at")
        batch_op.drop_column("jobs_failed")
        batch_op.drop_column("jobs_completed")
        batch_op.drop_column("slug")

    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_seller_id"), table_name="jobs")
    op.drop_table("jobs")