"""add exam task number to question bank

Revision ID: e1a2b3c4d5f6
Revises: 9f8c7b6a5d4e
Create Date: 2026-04-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "e1a2b3c4d5f6"
down_revision = "9f8c7b6a5d4e"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("question_bank_items")}

    if "exam_task_number" not in columns:
        op.add_column(
            "question_bank_items",
            sa.Column("exam_task_number", sa.Integer(), nullable=True),
        )

    op.execute("UPDATE question_bank_items SET exam_task_number = 1 WHERE exam_task_number IS NULL")
    op.alter_column("question_bank_items", "exam_task_number", nullable=False)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("question_bank_items")}

    if "exam_task_number" in columns:
        op.drop_column("question_bank_items", "exam_task_number")
