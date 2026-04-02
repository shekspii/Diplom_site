"""add subject to surveys

Revision ID: c5a8b2f5ef8d
Revises: 023d09684845
Create Date: 2026-04-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5a8b2f5ef8d'
down_revision = '023d09684845'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('surveys', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'subject',
                sa.String(length=255),
                nullable=False,
                server_default='Без предмета'
            )
        )


def downgrade():
    with op.batch_alter_table('surveys', schema=None) as batch_op:
        batch_op.drop_column('subject')
