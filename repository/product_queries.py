from models import Product, ThingType, Offer, Stock, Booking, PcObject
from repository.favorite_queries import get_favorites_for_offers
from repository.mediation_queries import get_mediations_for_offers
from repository.offer_queries import get_offers_by_productId
from repository.recommendation_queries import get_recommendations_for_offers
from repository.stock_queries import get_stocks_for_offers


class ProductWithBookingsException(Exception):
    pass


def delete_unwanted_existing_product(isbn: str):
    product_has_at_least_one_booking = Product.query \
                                           .filter_by(idAtProviders=isbn) \
                                           .join(Offer) \
                                           .join(Stock) \
                                           .join(Booking) \
                                           .count() > 0

    if product_has_at_least_one_booking:
        raise ProductWithBookingsException

    objects_to_delete = []
    product = find_thing_product_by_isbn_only_for_type_book(isbn)
    if product:
        objects_to_delete.append(product)
        offers = get_offers_by_productId(product.id)
        offer_ids = [offer.id for offer in offers]
        objects_to_delete = objects_to_delete + offers
        stocks = get_stocks_for_offers(offer_ids)
        objects_to_delete = objects_to_delete + stocks
        recommendations = get_recommendations_for_offers(offer_ids)
        mediations = get_mediations_for_offers(offer_ids)
        objects_to_delete = objects_to_delete + mediations
        favorites = get_favorites_for_offers(offer_ids)
        objects_to_delete = objects_to_delete + favorites
        objects_to_delete = objects_to_delete + recommendations
        PcObject.delete_all(objects_to_delete)


def find_by_id(product_id: int) -> Product:
    return Product.query.get(product_id)


def find_thing_product_by_isbn_only_for_type_book(isbn: str) -> Product:
    return Product.query.filter((Product.type == str(ThingType.LIVRE_EDITION)) &
                                (Product.idAtProviders == isbn)) \
        .one_or_none()