"""add audit entries and events

Revision ID: f2cffb6cf74d
Revises: 2ac0e53f682e
Create Date: 2026-10-27 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2cffb6cf74d"
down_revision: str | None = "2ac0e53f682e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the audit trail and the live event log."""
    op.create_table(
        "audit_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("verdict", sa.String(length=10), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_entries_payment_id"), "audit_entries", ["payment_id"], unique=False
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column("seller_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_index(op.f("ix_audit_entries_payment_id"), table_name="audit_entries")
    op.drop_table("audit_entries")
