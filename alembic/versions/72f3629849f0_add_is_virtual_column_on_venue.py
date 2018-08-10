"""Add isVirtual column on Venue table. It represents whether the venue is digital.

Revision ID: 72f3629849f0
Revises: e2960d28528f
Create Date: 2018-08-10 08:16:46.210630

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
from models.venue import CONSTRAINT_CHECK_IS_VIRTUAL_XOR_HAS_ADDRESS

revision = '72f3629849f0'
down_revision = 'e2960d28528f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('venue', sa.Column('isVirtual', sa.Boolean(), nullable=False))
    op.create_check_constraint(
        constraint_name='check_is_virtual_xor_has_address',
        table_name='venue',
        condition=CONSTRAINT_CHECK_IS_VIRTUAL_XOR_HAS_ADDRESS
    )


def downgrade():
    pass
