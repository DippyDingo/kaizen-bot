"""expand diary media fields

Revision ID: 20260306_000003
Revises: 20260306_000002
Create Date: 2026-03-06 03:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000003"
down_revision: Union[str, None] = "20260306_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "diary_entries",
        sa.Column("entry_type", sa.String(length=20), nullable=False, server_default="text"),
    )
    op.add_column("diary_entries", sa.Column("file_id", sa.String(length=255), nullable=True))
    op.add_column("diary_entries", sa.Column("file_unique_id", sa.String(length=255), nullable=True))
    op.add_column("diary_entries", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("diary_entries", sa.Column("duration_sec", sa.Integer(), nullable=True))
    op.add_column("diary_entries", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("diary_entries", sa.Column("height", sa.Integer(), nullable=True))

    op.alter_column("diary_entries", "entry_type", server_default=None)
    op.alter_column("diary_entries", "text", existing_type=sa.Text(), nullable=True)

    op.create_index(op.f("ix_diary_entries_entry_type"), "diary_entries", ["entry_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_diary_entries_entry_type"), table_name="diary_entries")

    op.alter_column("diary_entries", "text", existing_type=sa.Text(), nullable=False)

    op.drop_column("diary_entries", "height")
    op.drop_column("diary_entries", "width")
    op.drop_column("diary_entries", "duration_sec")
    op.drop_column("diary_entries", "mime_type")
    op.drop_column("diary_entries", "file_unique_id")
    op.drop_column("diary_entries", "file_id")
    op.drop_column("diary_entries", "entry_type")
