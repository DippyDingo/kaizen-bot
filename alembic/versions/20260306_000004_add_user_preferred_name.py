"""add preferred name to users

Revision ID: 20260306_000004
Revises: 20260306_000003
Create Date: 2026-03-06 17:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260306_000004"
down_revision: Union[str, None] = "20260306_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferred_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_name")
