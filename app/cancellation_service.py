from calendar_service import delete_booking_event

from sheet_service import (
    find_bookings,
    update_booking_status,
)


def cancel_booking_by_id(booking_id: str):
    matches = find_bookings(
        booking_id=booking_id
    )

    if not matches:
        return {
            "status": "not_found",
            "message": "No active booking found."
        }

    booking = matches[0]

    calendar_event_id = booking.get(
        "calendar_event_id"
    )

    if not calendar_event_id:
        return {
            "status": "error",
            "message": (
                "Booking was found, but no Calendar event ID "
                "is stored."
            )
        }

    # -----------------------------------------
    # Step 1: delete Calendar event
    # -----------------------------------------

    try:
        delete_booking_event(
            calendar_event_id
        )

    except Exception as exc:

        print(
            "Calendar cancellation error:",
            str(exc)
        )

        return {
            "status": "error",
            "message": (
                "Could not cancel the Calendar event."
            )
        }

    # -----------------------------------------
    # Step 2: update Google Sheet
    # -----------------------------------------

    try:
        update_booking_status(
            row_number=booking["row_number"],
            status="Cancelled"
        )

    except Exception as exc:

        print(
            "Sheet status update error:",
            str(exc)
        )

        return {
            "status": "partial_error",
            "message": (
                "Calendar event was cancelled, "
                "but Sheet status could not be updated."
            )
        }

    return {
        "status": "cancelled",
        "booking": booking,
        "message": (
            f"Booking {booking_id} has been cancelled."
        )
    }
