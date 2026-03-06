"""add dashboard message persistence

Revision ID: 20260306_000009
Revises: 20260306_000008
Create Date: 2026-03-06
"""

from alembic import op
import sqlalchemy as sa


revision = "20260306_000009"
down_revision = "20260306_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("dashboard_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("dashboard_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "dashboard_message_id")
    op.drop_column("users", "dashboard_chat_id")
