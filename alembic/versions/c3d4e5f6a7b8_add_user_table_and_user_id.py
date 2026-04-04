"""add user table and user_id to parcel

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-04 18:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"])

    op.add_column("parcel", sa.Column("user_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_parcel_user_id", "parcel", "user", ["user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_parcel_user_id", "parcel", type_="foreignkey")
    op.drop_column("parcel", "user_id")
    op.drop_index("ix_user_email", "user")
    op.drop_table("user")
