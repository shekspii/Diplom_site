"""add roles share keys and question bank

Revision ID: 9f8c7b6a5d4e
Revises: c5a8b2f5ef8d
Create Date: 2026-04-01 12:00:00.000000

"""
import secrets
import string

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '9f8c7b6a5d4e'
down_revision = 'c5a8b2f5ef8d'
branch_labels = None
depends_on = None


SHARE_KEY_ALPHABET = string.ascii_uppercase + string.digits


def _generate_share_key(existing_keys, length=10):
    while True:
        share_key = "".join(secrets.choice(SHARE_KEY_ALPHABET) for _ in range(length))
        if share_key not in existing_keys:
            existing_keys.add(share_key)
            return share_key


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    user_role_enum = postgresql.ENUM("user", "admin", name="user_role")
    survey_access_mode_enum = postgresql.ENUM("private", "by_key", name="survey_access_mode")
    test_session_status_enum = postgresql.ENUM("generated", "completed", "cancelled", name="test_session_status")
    question_type_enum = postgresql.ENUM(
        "single",
        "multiple",
        "text",
        name="question_type",
        create_type=False
    )

    user_role_enum.create(bind, checkfirst=True)
    survey_access_mode_enum.create(bind, checkfirst=True)
    test_session_status_enum.create(bind, checkfirst=True)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "role" not in user_columns:
        with op.batch_alter_table("users", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("role", user_role_enum, nullable=False, server_default="user")
            )

    survey_columns = {column["name"] for column in inspector.get_columns("surveys")}
    if "share_key" not in survey_columns or "access_mode" not in survey_columns:
        with op.batch_alter_table("surveys", schema=None) as batch_op:
            if "share_key" not in survey_columns:
                batch_op.add_column(sa.Column("share_key", sa.String(length=32), nullable=True))
            if "access_mode" not in survey_columns:
                batch_op.add_column(
                    sa.Column(
                        "access_mode",
                        survey_access_mode_enum,
                        nullable=False,
                        server_default="by_key"
                    )
                )

    inspector = inspect(bind)
    survey_columns = {column["name"] for column in inspector.get_columns("surveys")}
    if "share_key" in survey_columns:
        existing_keys = {
            row[0]
            for row in bind.execute(sa.text("SELECT share_key FROM surveys WHERE share_key IS NOT NULL")).fetchall()
        }
        survey_rows = bind.execute(sa.text("SELECT id, share_key FROM surveys")).fetchall()
        for survey_id, current_key in survey_rows:
            if current_key:
                existing_keys.add(current_key)
                continue

            share_key = _generate_share_key(existing_keys)
            bind.execute(
                sa.text(
                    "UPDATE surveys SET share_key = :share_key WHERE id = :survey_id"
                ),
                {"share_key": share_key, "survey_id": survey_id},
            )

    survey_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("surveys")}
    if "share_key" in survey_columns:
        with op.batch_alter_table("surveys", schema=None) as batch_op:
            batch_op.alter_column("share_key", existing_type=sa.String(length=32), nullable=False)
            if "uq_surveys_share_key" not in survey_constraints:
                batch_op.create_unique_constraint("uq_surveys_share_key", ["share_key"])

    response_columns = {column["name"] for column in inspector.get_columns("responses")}
    if "user_id" in response_columns:
        with op.batch_alter_table("responses", schema=None) as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)

    if "question_bank_items" not in existing_tables:
        op.create_table(
            "question_bank_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("topic", sa.String(length=255), nullable=True),
            sa.Column("difficulty", sa.String(length=50), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("type", question_type_enum, nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "question_bank_options" not in existing_tables:
        op.create_table(
            "question_bank_options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.ForeignKeyConstraint(["question_id"], ["question_bank_items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("question_id", "position", name="uq_bank_question_option_position"),
        )

    if "test_sessions" not in existing_tables:
        op.create_table(
            "test_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("requested_count", sa.Integer(), nullable=False),
            sa.Column("status", test_session_status_enum, nullable=False, server_default="generated"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "test_session_questions" not in existing_tables:
        op.create_table(
            "test_session_questions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("bank_question_id", sa.Integer(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["bank_question_id"], ["question_bank_items.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["test_sessions.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id", "position", name="uq_test_session_position"),
        )


def downgrade():
    bind = op.get_bind()

    user_role_enum = postgresql.ENUM("user", "admin", name="user_role")
    survey_access_mode_enum = postgresql.ENUM("private", "by_key", name="survey_access_mode")
    test_session_status_enum = postgresql.ENUM("generated", "completed", "cancelled", name="test_session_status")

    op.drop_table("test_session_questions")
    op.drop_table("test_sessions")
    op.drop_table("question_bank_options")
    op.drop_table("question_bank_items")

    with op.batch_alter_table("responses", schema=None) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("surveys", schema=None) as batch_op:
        batch_op.drop_constraint("uq_surveys_share_key", type_="unique")
        batch_op.drop_column("access_mode")
        batch_op.drop_column("share_key")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("role")

    test_session_status_enum.drop(bind, checkfirst=True)
    survey_access_mode_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
