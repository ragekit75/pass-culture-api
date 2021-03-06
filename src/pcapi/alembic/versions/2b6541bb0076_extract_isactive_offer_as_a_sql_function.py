"""extract_isActive_offer_as_a_sql_function

Revision ID: 2b6541bb0076
Revises: 747f6c0639b0
Create Date: 2020-04-06 08:51:38.455156

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "2b6541bb0076"
down_revision = "747f6c0639b0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE OR REPLACE FUNCTION get_active_offers_ids(with_mediation bool)
        RETURNS SETOF BIGINT AS
        $body$
        BEGIN
            RETURN QUERY
            SELECT DISTINCT ON (offer.id) offer.id
            FROM offer
            JOIN venue ON offer."venueId" = venue.id
            JOIN offerer ON offerer.id = venue."managingOffererId"
            WHERE offer."isActive" = TRUE
                AND venue."validationToken" IS NULL
                AND (
                    NOT with_mediation
                    OR (with_mediation AND EXISTS (SELECT * FROM offer_has_at_least_one_active_mediation(offer.id)))
                )
                AND (EXISTS (SELECT * FROM offer_has_at_least_one_bookable_stock(offer.id)))
                AND offerer."isActive" = TRUE
                AND offerer."validationToken" IS NULL
                AND offer.type != 'ThingType.ACTIVATION'
                AND offer.type != 'EventType.ACTIVATION';
        END;
        $body$
        LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
            CREATE OR REPLACE FUNCTION get_recommendable_offers_ordered_by_digital_offers()
            RETURNS TABLE (
                criterion_score BIGINT,
                id BIGINT,
                "venueId" BIGINT,
                type VARCHAR,
                name VARCHAR,
                url VARCHAR,
                "isNational" BOOLEAN,
                partitioned_offers BIGINT
            ) AS $body$
            BEGIN
                RETURN QUERY
                SELECT
                    (SELECT * FROM get_offer_score(offer.id)) AS criterion_score,
                    offer.id AS id,
                    offer."venueId" AS "venueId",
                    offer.type AS type,
                    offer.name AS name,
                    offer.url AS url,
                    offer."isNational" AS "isNational",
                    ROW_NUMBER() OVER (
                        ORDER BY
                            offer.url IS NOT NULL DESC,
                            (EXISTS (SELECT 1 FROM stock WHERE stock."offerId" = offer.id AND stock."beginningDatetime" > '2020-04-25T00:00:00'::TIMESTAMP)) DESC,
                            (
                                SELECT COALESCE(SUM(criterion."scoreDelta"), 0) AS coalesce_1
                                FROM criterion, offer_criterion
                                WHERE criterion.id = offer_criterion."criterionId"
                                    AND offer_criterion."offerId" = offer.id
                            ) DESC,
                            RANDOM()
                    ) AS partitioned_offers
                FROM offer
                WHERE offer.id IN (SELECT * FROM get_active_offers_ids(TRUE))
                ORDER BY ROW_NUMBER() OVER (
                    ORDER BY
                        offer.url IS NOT NULL DESC,
                        (EXISTS (SELECT 1 FROM stock WHERE stock."offerId" = offer.id AND stock."beginningDatetime" > '2020-04-25T00:00:00'::TIMESTAMP)) DESC,
                        (
                            SELECT COALESCE(SUM(criterion."scoreDelta"), 0) AS coalesce_1
                            FROM criterion, offer_criterion
                            WHERE criterion.id = offer_criterion."criterionId"
                                AND offer_criterion."offerId" = offer.id
                        ) DESC,
                        RANDOM()
                );
            END
            $body$
            LANGUAGE plpgsql;
        """
    )


def downgrade():
    op.execute(
        """
            CREATE OR REPLACE FUNCTION get_recommendable_offers_ordered_by_digital_offers()
            RETURNS TABLE (
                criterion_score BIGINT,
                id BIGINT,
                "venueId" BIGINT,
                type VARCHAR,
                name VARCHAR,
                url VARCHAR,
                "isNational" BOOLEAN,
                partitioned_offers BIGINT
            ) AS $body$
            BEGIN
                RETURN QUERY
                SELECT
                    (SELECT * FROM get_offer_score(offer.id)) AS criterion_score,
                    offer.id AS id,
                    offer."venueId" AS "venueId",
                    offer.type AS type,
                    offer.name AS name,
                    offer.url AS url,
                    offer."isNational" AS "isNational",
                    ROW_NUMBER() OVER (
                        ORDER BY
                            offer.url IS NOT NULL DESC,
                            (EXISTS (SELECT 1 FROM stock WHERE stock."offerId" = offer.id AND stock."beginningDatetime" > '2020-04-25T00:00:00'::TIMESTAMP)) DESC,
                            (
                                SELECT COALESCE(SUM(criterion."scoreDelta"), 0) AS coalesce_1
                                FROM criterion, offer_criterion
                                WHERE criterion.id = offer_criterion."criterionId"
                                    AND offer_criterion."offerId" = offer.id
                            ) DESC,
                            RANDOM()
                    ) AS partitioned_offers
                FROM offer
                WHERE offer.id IN (
                    SELECT DISTINCT ON (offer.id) offer.id
                    FROM offer
                    JOIN venue ON offer."venueId" = venue.id
                    JOIN offerer ON offerer.id = venue."managingOffererId"
                    WHERE offer."isActive" = TRUE
                        AND venue."validationToken" IS NULL
                        AND (EXISTS (SELECT * FROM offer_has_at_least_one_active_mediation(offer.id)))
                        AND (EXISTS (SELECT * FROM offer_has_at_least_one_bookable_stock(offer.id)))
                        AND offerer."isActive" = TRUE
                        AND offerer."validationToken" IS NULL
                        AND offer.type != 'ThingType.ACTIVATION'
                        AND offer.type != 'EventType.ACTIVATION'
                )
                ORDER BY ROW_NUMBER() OVER (
                    ORDER BY
                        offer.url IS NOT NULL DESC,
                        (EXISTS (SELECT 1 FROM stock WHERE stock."offerId" = offer.id AND stock."beginningDatetime" > '2020-04-25T00:00:00'::TIMESTAMP)) DESC,
                        (
                            SELECT COALESCE(SUM(criterion."scoreDelta"), 0) AS coalesce_1
                            FROM criterion, offer_criterion
                            WHERE criterion.id = offer_criterion."criterionId"
                                AND offer_criterion."offerId" = offer.id
                        ) DESC,
                        RANDOM()
                );
            END
            $body$
            LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        DROP FUNCTION IF EXISTS get_active_offers_ids;
        """
    )
