"""add awaiting_user payment state

Revision ID: de8f846b8465
Revises: 457c2d70f9f7
Create Date: 2026-10-22 10:20:15.260764

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'de8f846b8465'
down_revision: str | Sequence[str] | None = '457c2d70f9f7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_STATES = (
    "PROPOSED", "APPROVED", "HELD", "VERIFIED", "RELEASED", "REFUNDED", "BLOCKED",
)
NEW_STATES = (
    "PROPOSED", "AWAITING_USER", "APPROVED", "HELD", "VERIFIED",
    "RELEASED", "REFUNDED", "BLOCKED",
)


def upgrade() -> None:
    """Add the awaiting_user state and store it as plain text (room for 20 characters)."""
    with op.batch_alter_table("payments") as batch_op:
        batch_op.alter_column(
            "state",
            existing_type=sa.Enum(*OLD_STATES, name="paymentstate"),
            type_=sa.Enum(*NEW_STATES, name="paymentstate", native_enum=False, length=20),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Only safe while no payment is waiting for the user."""
    with op.batch_alter_table("payments") as batch_op:
        batch_op.alter_column(
            "state",
            existing_type=sa.Enum(*NEW_STATES, name="paymentstate", native_enum=False, length=20),
            type_=sa.Enum(*OLD_STATES, name="paymentstate"),
            existing_nullable=False,
        )