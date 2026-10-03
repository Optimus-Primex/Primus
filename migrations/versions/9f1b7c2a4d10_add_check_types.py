"""add monitor check types

Adds the pluggable check-type columns:
  * ``monitors.type``         - registered check type slug (default "http")
  * ``monitors.type_config``  - JSON configuration for the type
  * ``checks.detail``         - JSON metrics captured by a check

Revision ID: 9f1b7c2a4d10
Revises: 3c6984054500
Create Date: 2026-10-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1b7c2a4d10'
down_revision = '3c6984054500'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('monitors', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('type', sa.String(length=32), nullable=False, server_default='http')
        )
        batch_op.add_column(
            sa.Column('type_config', sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )
        # Not every check type needs a target URL.
        batch_op.alter_column(
            'url', existing_type=sa.String(length=2048), nullable=True
        )

    with op.batch_alter_table('checks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('detail', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('checks', schema=None) as batch_op:
        batch_op.drop_column('detail')

    with op.batch_alter_table('monitors', schema=None) as batch_op:
        batch_op.alter_column(
            'url', existing_type=sa.String(length=2048), nullable=False
        )
        batch_op.drop_column('type_config')
        batch_op.drop_column('type')
