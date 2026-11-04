"""add mission tellings and per-session story index

Revision ID: 9c4d1e2f7a35
Revises: f27a8f609093
Create Date: 2026-10-31 09:12:04.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4d1e2f7a35'
down_revision: Union[str, None] = 'f27a8f609093'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('missions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('stories', sa.JSON(), nullable=False, server_default='[]')
        )

    with op.batch_alter_table('progress', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('story_index', sa.Integer(), nullable=False, server_default='0')
        )


def downgrade() -> None:
    with op.batch_alter_table('progress', schema=None) as batch_op:
        batch_op.drop_column('story_index')

    with op.batch_alter_table('missions', schema=None) as batch_op:
        batch_op.drop_column('stories')
