"""add submissions and job tests

Revision ID: 2ac0e53f682e
Revises: 02c6ac62a711
Create Date: 2026-10-26 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ac0e53f682e"
down_revision: str | None = "02c6ac62a711"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the submissions table and the agreed test code on each job."""
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_submissions_job_id"), "submissions", ["job_id"], unique=False)
    op.create_index(
        op.f("ix_submissions_seller_id"), "submissions", ["seller_id"], unique=False
    )

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("test_code", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("test_code")

    op.drop_index(op.f("ix_submissions_seller_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_job_id"), table_name="submissions")
    op.drop_table("submissions")
