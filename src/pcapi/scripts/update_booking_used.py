from datetime import datetime

import pcapi.core.bookings.repository as booking_repository
from pcapi.repository import repository


def update_booking_used_after_stock_occurrence():
    bookings_to_process = booking_repository.find_not_used_and_not_cancelled()
    bookings_id_errors = []

    for booking in bookings_to_process:
        if booking.stock.beginningDatetime:
            now = datetime.utcnow()
            if not booking.stock.isEventDeletable:
                booking.isUsed = True
                booking.dateUsed = now
                try:
                    repository.save(booking)
                except Exception:  # pylint: disable=broad-except
                    bookings_id_errors.append(booking.id)

    print("Bookings id in error %s" % bookings_id_errors)
