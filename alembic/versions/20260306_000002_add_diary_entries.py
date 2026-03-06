"""add diary entries

Revision ID: 20260306_000002
Revises: 20260306_000001
Create Date: 2026-03-06 02:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000002"
down_revision: Union[str, None] = "20260306_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diary_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diary_entries_user_id"), "diary_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_diary_entries_created_at"), "diary_entries", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_diary_entries_created_at"), table_name="diary_entries")
    op.drop_index(op.f("ix_diary_entries_user_id"), table_name="diary_entries")
    op.drop_table("diary_entries")
