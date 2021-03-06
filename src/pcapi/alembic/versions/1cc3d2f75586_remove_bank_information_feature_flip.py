"""remove_bank_information_feature_flip

Revision ID: 1cc3d2f75586
Revises: 3a5629a53c17
Create Date: 2020-05-26 15:06:20.076645

"""
import enum

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1cc3d2f75586"
down_revision = "3a5629a53c17"
branch_labels = None
depends_on = None


class FeatureToggle(enum.Enum):
    NEW_RIBS_UPLOAD = "Permettre aux utilisateurs duploader leur ribs via la nouvelle démarche DMS"


def upgrade():
    new_values = (
        "WEBAPP_SIGNUP",
        "DEGRESSIVE_REIMBURSEMENT_RATE",
        "QR_CODE",
        "FULL_OFFERS_SEARCH_WITH_OFFERER_AND_VENUE",
        "SEARCH_ALGOLIA",
        "SEARCH_LEGACY",
        "BENEFICIARIES_IMPORT",
        "SYNCHRONIZE_ALGOLIA",
        "SYNCHRONIZE_ALLOCINE",
        "SYNCHRONIZE_BANK_INFORMATION",
        "SYNCHRONIZE_LIBRAIRES",
        "SYNCHRONIZE_TITELIVE",
        "SYNCHRONIZE_TITELIVE_PRODUCTS",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS",
        "UPDATE_DISCOVERY_VIEW",
        "UPDATE_BOOKING_USED",
        "RECOMMENDATIONS_WITH_DISCOVERY_VIEW",
        "RECOMMENDATIONS_WITH_DIGITAL_FIRST",
        "RECOMMENDATIONS_WITH_GEOLOCATION",
        "BOOKINGS_V2",
        "SAVE_SEEN_OFFERS",
    )
    previous_values = (
        "WEBAPP_SIGNUP",
        "DEGRESSIVE_REIMBURSEMENT_RATE",
        "QR_CODE",
        "FULL_OFFERS_SEARCH_WITH_OFFERER_AND_VENUE",
        "SEARCH_ALGOLIA",
        "SEARCH_LEGACY",
        "BENEFICIARIES_IMPORT",
        "SYNCHRONIZE_ALGOLIA",
        "SYNCHRONIZE_ALLOCINE",
        "SYNCHRONIZE_BANK_INFORMATION",
        "SYNCHRONIZE_LIBRAIRES",
        "SYNCHRONIZE_TITELIVE",
        "SYNCHRONIZE_TITELIVE_PRODUCTS",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS",
        "UPDATE_DISCOVERY_VIEW",
        "UPDATE_BOOKING_USED",
        "RECOMMENDATIONS_WITH_DISCOVERY_VIEW",
        "RECOMMENDATIONS_WITH_DIGITAL_FIRST",
        "RECOMMENDATIONS_WITH_GEOLOCATION",
        "BOOKINGS_V2",
        "SAVE_SEEN_OFFERS",
        "NEW_RIBS_UPLOAD",
    )

    previous_enum = sa.Enum(*previous_values, name="featuretoggle")
    new_enum = sa.Enum(*new_values, name="featuretoggle")
    temporary_enum = sa.Enum(*new_values, name="tmp_featuretoggle")

    op.execute("DELETE FROM feature WHERE name = 'NEW_RIBS_UPLOAD'")
    temporary_enum.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE feature ALTER COLUMN name TYPE tmp_featuretoggle USING name::text::tmp_featuretoggle")
    previous_enum.drop(op.get_bind(), checkfirst=False)
    new_enum.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE feature ALTER COLUMN name TYPE featuretoggle USING name::text::featuretoggle")
    temporary_enum.drop(op.get_bind(), checkfirst=False)


def downgrade():
    new_values = (
        "WEBAPP_SIGNUP",
        "DEGRESSIVE_REIMBURSEMENT_RATE",
        "QR_CODE",
        "FULL_OFFERS_SEARCH_WITH_OFFERER_AND_VENUE",
        "SEARCH_ALGOLIA",
        "SEARCH_LEGACY",
        "BENEFICIARIES_IMPORT",
        "SYNCHRONIZE_ALGOLIA",
        "SYNCHRONIZE_ALLOCINE",
        "SYNCHRONIZE_BANK_INFORMATION",
        "SYNCHRONIZE_LIBRAIRES",
        "SYNCHRONIZE_TITELIVE",
        "SYNCHRONIZE_TITELIVE_PRODUCTS",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS",
        "UPDATE_DISCOVERY_VIEW",
        "UPDATE_BOOKING_USED",
        "RECOMMENDATIONS_WITH_DISCOVERY_VIEW",
        "RECOMMENDATIONS_WITH_DIGITAL_FIRST",
        "RECOMMENDATIONS_WITH_GEOLOCATION",
        "BOOKINGS_V2",
        "SAVE_SEEN_OFFERS",
        "NEW_RIBS_UPLOAD",
    )
    previous_values = (
        "WEBAPP_SIGNUP",
        "DEGRESSIVE_REIMBURSEMENT_RATE",
        "QR_CODE",
        "FULL_OFFERS_SEARCH_WITH_OFFERER_AND_VENUE",
        "SEARCH_ALGOLIA",
        "SEARCH_LEGACY",
        "BENEFICIARIES_IMPORT",
        "SYNCHRONIZE_ALGOLIA",
        "SYNCHRONIZE_ALLOCINE",
        "SYNCHRONIZE_BANK_INFORMATION",
        "SYNCHRONIZE_LIBRAIRES",
        "SYNCHRONIZE_TITELIVE",
        "SYNCHRONIZE_TITELIVE_PRODUCTS",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION",
        "SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS",
        "UPDATE_DISCOVERY_VIEW",
        "UPDATE_BOOKING_USED",
        "RECOMMENDATIONS_WITH_DIGITAL_FIRST",
        "RECOMMENDATIONS_WITH_DISCOVERY_VIEW",
        "RECOMMENDATIONS_WITH_GEOLOCATION",
        "BOOKINGS_V2",
        "SAVE_SEEN_OFFERS",
    )

    previous_enum = sa.Enum(*previous_values, name="featuretoggle")
    new_enum = sa.Enum(*new_values, name="featuretoggle")
    temporary_enum = sa.Enum(*new_values, name="tmp_featuretoggle")

    temporary_enum.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE feature ALTER COLUMN name TYPE tmp_featuretoggle USING name::text::tmp_featuretoggle")
    previous_enum.drop(op.get_bind(), checkfirst=False)
    new_enum.create(op.get_bind(), checkfirst=False)
    op.execute("ALTER TABLE feature ALTER COLUMN name TYPE featuretoggle USING name::text::featuretoggle")
    op.execute(
        """
            INSERT INTO feature (name, description, "isActive")
            VALUES ('%s', '%s', FALSE);
            """
        % (FeatureToggle.NEW_RIBS_UPLOAD.name, FeatureToggle.NEW_RIBS_UPLOAD.value)
    )
    temporary_enum.drop(op.get_bind(), checkfirst=False)
