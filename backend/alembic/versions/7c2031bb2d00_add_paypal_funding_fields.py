"""add paypal funding fields

Revision ID: 7c2031bb2d00
Revises: 99c8634dd69f
Create Date: 2026-10-31 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c2031bb2d00"
down_revision: str | None = "99c8634dd69f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remember the PayPal capture, and where the buyer approves the hold."""
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("paypal_capture_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("approve_url", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("approve_url")
        batch_op.drop_column("paypal_capture_id")
