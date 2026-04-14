"""add test submissions

Revision ID: a1b2c3d4e5f6
Revises: f2b3c4d5e6f7
Create Date: 2026-04-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "test_submissions" not in existing_tables:
        op.create_table(
            "test_submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_questions", sa.Integer(), nullable=False),
            sa.Column("submitted_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["test_sessions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id"),
        )

    if "test_submission_answers" not in existing_tables:
        op.create_table(
            "test_submission_answers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("bank_question_id", sa.Integer(), nullable=False),
            sa.Column("text_answer", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["submission_id"], ["test_submissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["bank_question_id"], ["question_bank_items.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "test_submission_answer_options" not in existing_tables:
        op.create_table(
            "test_submission_answer_options",
            sa.Column("answer_id", sa.Integer(), nullable=False),
            sa.Column("option_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["answer_id"], ["test_submission_answers.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["option_id"], ["question_bank_options.id"]),
            sa.PrimaryKeyConstraint("answer_id", "option_id"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "test_submission_answer_options" in existing_tables:
        op.drop_table("test_submission_answer_options")
    if "test_submission_answers" in existing_tables:
        op.drop_table("test_submission_answers")
    if "test_submissions" in existing_tables:
        op.drop_table("test_submissions")
