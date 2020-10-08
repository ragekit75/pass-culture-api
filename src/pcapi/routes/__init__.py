from pcapi.utils.config import IS_DEV


def install_routes():
    import pcapi.routes.bank_informations
    import pcapi.routes.beneficiaries
    import pcapi.routes.bookings
    import pcapi.routes.error_handlers
    import pcapi.routes.export
    import pcapi.routes.favorites
    import pcapi.routes.features
    import pcapi.routes.mediations
    import pcapi.routes.music_types
    import pcapi.routes.offers
    import pcapi.routes.offerers
    import pcapi.routes.signup
    import pcapi.routes.show_types
    import pcapi.routes.stocks
    import pcapi.routes.passwords
    import pcapi.routes.providers
    import pcapi.routes.recommendations
    import pcapi.routes.reimbursements
    import pcapi.routes.seen_offers
    import pcapi.routes.storage
    import pcapi.routes.types
    import pcapi.routes.user_offerers
    import pcapi.routes.users
    import pcapi.routes.validate
    import pcapi.routes.venue_providers
    import pcapi.routes.venues
    import pcapi.routes.venue_types
    import pcapi.routes.venue_labels
    import pcapi.routes.health_check
    import pcapi.routes.mailing_contacts

    if IS_DEV:
        import pcapi.routes.sandboxes