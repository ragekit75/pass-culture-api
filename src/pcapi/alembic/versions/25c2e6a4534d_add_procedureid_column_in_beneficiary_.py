"""add_procedureId_column_in_beneficiary_import_table

Revision ID: 25c2e6a4534d
Revises: 5c0507247814
Create Date: 2020-04-09 13:30:59.562210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "25c2e6a4534d"
down_revision = "5c0507247814"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("beneficiary_import", sa.Column("demarcheSimplifieeProcedureId", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("beneficiary_import", "demarcheSimplifieeProcedureId")
