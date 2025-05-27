"""seed parcel types

Revision ID: 0c8ee6e20a41
Revises: 45dd304438ec
Create Date: 2025-05-27 20:15:45.227043

"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import insert as mysql_insert

# revision identifiers, used by Alembic.
revision: str = "0c8ee6e20a41"
down_revision: Union[str, None] = "45dd304438ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    parcel_type = sa.table(
        "parcel_type",
        sa.column("id", sa.String(36)),
        sa.column("name", sa.String(50)),
    )

    defaults = ("clothes", "electronics", "misc")

    # one INSERT ... ON DUPLICATE KEY UPDATE  (# MySQL-specific, идемпотентно)
    values = [{"id": str(uuid4()), "name": n} for n in defaults]
    stmt = mysql_insert(parcel_type).values(values)
    stmt = stmt.on_duplicate_key_update(name=stmt.inserted.name)

    op.execute(stmt)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM parcel_type WHERE name IN ('clothes','electronics','misc')")
