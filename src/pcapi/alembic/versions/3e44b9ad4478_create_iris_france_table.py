"""create_iris_france_table

Revision ID: 3e44b9ad4478
Revises: 771cab29d46e
Create Date: 2020-02-25 18:30:52.946282

"""
from alembic import op
from geoalchemy2.types import Geometry
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3e44b9ad4478"
down_revision = "03f3f93489ab"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "iris_france",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("irisCode", sa.VARCHAR(9), nullable=False),
        sa.Column("centroid", Geometry(geometry_type="POINT"), nullable=False),
        sa.Column("shape", Geometry(srid=4326), nullable=False),
    )


def downgrade():
    op.drop_table("iris_france")
