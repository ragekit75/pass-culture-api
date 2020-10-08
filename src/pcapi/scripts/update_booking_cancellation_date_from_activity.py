from sqlalchemy import text

from pcapi.models import BookingSQLEntity
from pcapi.repository import repository


def update_booking_cancellation_date_from_activity():
    bookings_to_update = BookingSQLEntity.query.filter(
        (BookingSQLEntity.cancellationDate == None),
        (BookingSQLEntity.isCancelled == True)
    ).all()

    for booking in bookings_to_update:
        last_activity = booking.activity() \
            .filter(
                text("cast((changed_data->>'isCancelled') AS boolean) = true")
            ) \
            .first()

        booking.cancellationDate = last_activity.issued_at
        repository.save(booking)