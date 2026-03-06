"""add medication logs

Revision ID: 20260306_000007
Revises: 20260306_000006
Create Date: 2026-03-06 23:35:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000007"
down_revision: Union[str, None] = "20260306_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("dose", sa.String(length=120), nullable=False),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_medication_logs_logged_at"), "medication_logs", ["logged_at"], unique=False)
    op.create_index(op.f("ix_medication_logs_user_id"), "medication_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_medication_logs_user_id"), table_name="medication_logs")
    op.drop_index(op.f("ix_medication_logs_logged_at"), table_name="medication_logs")
    op.drop_table("medication_logs")
