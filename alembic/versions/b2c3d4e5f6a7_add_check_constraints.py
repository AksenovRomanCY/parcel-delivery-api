"""add check constraints

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 18:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_parcel_weight_positive",
        "parcel",
        "weight_kg > 0",
    )
    op.create_check_constraint(
        "ck_parcel_value_non_negative",
        "parcel",
        "declared_value_usd >= 0",
    )
    op.create_check_constraint(
        "ck_parcel_cost_non_negative",
        "parcel",
        "delivery_cost_rub >= 0 OR delivery_cost_rub IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint("ck_parcel_weight_positive", "parcel", type_="check")
    op.drop_constraint("ck_parcel_value_non_negative", "parcel", type_="check")
    op.drop_constraint("ck_parcel_cost_non_negative", "parcel", type_="check")
