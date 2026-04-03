"""float_to_decimal

Revision ID: a1b2c3d4e5f6
Revises: 0c8ee6e20a41
Create Date: 2026-04-04 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "0c8ee6e20a41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "parcel",
        "weight_kg",
        existing_type=sa.Float(),
        type_=sa.Numeric(10, 3),
        existing_nullable=False,
    )
    op.alter_column(
        "parcel",
        "declared_value_usd",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "parcel",
        "delivery_cost_rub",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "parcel",
        "weight_kg",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "parcel",
        "declared_value_usd",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "parcel",
        "delivery_cost_rub",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        existing_nullable=True,
    )
