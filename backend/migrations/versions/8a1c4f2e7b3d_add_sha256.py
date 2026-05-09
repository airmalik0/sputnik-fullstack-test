"""add sha256 column to files

Revision ID: 8a1c4f2e7b3d
Revises: 0d6439d2e79f
Create Date: 2026-05-09 11:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a1c4f2e7b3d"
down_revision: Union[str, Sequence[str], None] = "0d6439d2e79f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable so existing rows don't need a backfill — a future job can
    # rehash on demand. Adding a NOT NULL with default would force a
    # table rewrite, which we deliberately avoid.
    op.add_column(
        "files",
        sa.Column("sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("files", "sha256")
