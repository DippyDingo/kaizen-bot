"""add chat keyboard message ref

Revision ID: 20260306_000011
Revises: 20260306_000010
Create Date: 2026-03-08
"""

from alembic import op
import sqlalchemy as sa


revision = "20260306_000011"
down_revision = "20260306_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("chat_keyboard_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("chat_keyboard_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "chat_keyboard_message_id")
    op.drop_column("users", "chat_keyboard_chat_id")
