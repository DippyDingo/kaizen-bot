"""add user daily targets

Revision ID: 20260306_000006
Revises: 20260306_000005
Create Date: 2026-03-06 23:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000006"
down_revision: Union[str, None] = "20260306_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("daily_water_target_ml", sa.Integer(), nullable=False, server_default="2500"))
    op.add_column("users", sa.Column("daily_workout_target_min", sa.Integer(), nullable=False, server_default="30"))
    op.alter_column("users", "daily_water_target_ml", server_default=None)
    op.alter_column("users", "daily_workout_target_min", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "daily_workout_target_min")
    op.drop_column("users", "daily_water_target_ml")
