"""add correct text answer to question bank

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5f6
Create Date: 2026-04-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "f2b3c4d5e6f7"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("question_bank_items")}

    if "correct_text_answer" not in columns:
        op.add_column(
            "question_bank_items",
            sa.Column("correct_text_answer", sa.Text(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("question_bank_items")}

    if "correct_text_answer" in columns:
        op.drop_column("question_bank_items", "correct_text_answer")
