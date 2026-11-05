"""add user role and seller link

Revision ID: b3f1c9a27d54
Revises: 7c2031bb2d00
Create Date: 2026-11-04 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f1c9a27d54"
down_revision: str | None = "7c2031bb2d00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Say whether an account is a buyer or a seller, and link a seller account to its seller."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=10), server_default="buyer", nullable=False)
        )
        batch_op.add_column(sa.Column("seller_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_users_seller_id", "sellers", ["seller_id"], ["id"])
        batch_op.create_unique_constraint("uq_users_seller_id", ["seller_id"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_seller_id", type_="unique")
        batch_op.drop_constraint("fk_users_seller_id", type_="foreignkey")
        batch_op.drop_column("seller_id")
        batch_op.drop_column("role")