"""add wellbeing logs

Revision ID: 20260306_000010
Revises: 20260306_000009
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260306_000010"
down_revision = "20260306_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wellbeing_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("logged_date", sa.Date(), nullable=False),
        sa.Column("energy_level", sa.Integer(), nullable=False),
        sa.Column("stress_level", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "logged_date", name="uq_wellbeing_logs_user_day"),
    )
    op.create_index(op.f("ix_wellbeing_logs_logged_date"), "wellbeing_logs", ["logged_date"], unique=False)
    op.create_index(op.f("ix_wellbeing_logs_user_id"), "wellbeing_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wellbeing_logs_user_id"), table_name="wellbeing_logs")
    op.drop_index(op.f("ix_wellbeing_logs_logged_date"), table_name="wellbeing_logs")
    op.drop_table("wellbeing_logs")
