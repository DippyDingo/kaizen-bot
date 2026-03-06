"""add medication courses and schedule status

Revision ID: 20260306_000008
Revises: 20260306_000007
Create Date: 2026-03-06 23:55:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260306_000008"
down_revision: Union[str, None] = "20260306_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_courses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("dose", sa.String(length=120), nullable=False),
        sa.Column("intake_time", sa.Time(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_medication_courses_end_date"), "medication_courses", ["end_date"], unique=False)
    op.create_index(op.f("ix_medication_courses_start_date"), "medication_courses", ["start_date"], unique=False)
    op.create_index(op.f("ix_medication_courses_user_id"), "medication_courses", ["user_id"], unique=False)

    op.add_column("medication_logs", sa.Column("course_id", sa.Integer(), nullable=True))
    op.add_column("medication_logs", sa.Column("scheduled_date", sa.Date(), nullable=True))
    op.add_column("medication_logs", sa.Column("status", sa.String(length=16), nullable=False, server_default="taken"))
    op.create_index(op.f("ix_medication_logs_course_id"), "medication_logs", ["course_id"], unique=False)
    op.create_index(op.f("ix_medication_logs_scheduled_date"), "medication_logs", ["scheduled_date"], unique=False)
    op.create_foreign_key(
        "fk_medication_logs_course_id_medication_courses",
        "medication_logs",
        "medication_courses",
        ["course_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute("UPDATE medication_logs SET scheduled_date = DATE(logged_at), status = 'taken' WHERE scheduled_date IS NULL")
    op.alter_column("medication_logs", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_medication_logs_course_id_medication_courses", "medication_logs", type_="foreignkey")
    op.drop_index(op.f("ix_medication_logs_scheduled_date"), table_name="medication_logs")
    op.drop_index(op.f("ix_medication_logs_course_id"), table_name="medication_logs")
    op.drop_column("medication_logs", "status")
    op.drop_column("medication_logs", "scheduled_date")
    op.drop_column("medication_logs", "course_id")

    op.drop_index(op.f("ix_medication_courses_user_id"), table_name="medication_courses")
    op.drop_index(op.f("ix_medication_courses_start_date"), table_name="medication_courses")
    op.drop_index(op.f("ix_medication_courses_end_date"), table_name="medication_courses")
    op.drop_table("medication_courses")
