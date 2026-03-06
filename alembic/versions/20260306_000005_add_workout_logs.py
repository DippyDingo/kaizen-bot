"""add workout logs

Revision ID: 20260306_000005
Revises: 20260306_000004
Create Date: 2026-03-06 22:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000005"
down_revision: Union[str, None] = "20260306_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workout_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("workout_type", sa.String(length=32), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_logs_user_id"), "workout_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_workout_logs_logged_at"), "workout_logs", ["logged_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_logs_logged_at"), table_name="workout_logs")
    op.drop_index(op.f("ix_workout_logs_user_id"), table_name="workout_logs")
    op.drop_table("workout_logs")
