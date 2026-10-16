from calendar_service import (
    update_booking_event,
    is_slot_available,
)

from sheet_service import (
    find_bookings,
    update_booking_datetime,
)


# ============================================================
# Reschedule permanent booking
# ============================================================

def reschedule_booking(
    booking_id: str,
    new_date: str,
    new_time: str,
):

    matches = find_bookings(
        booking_id=booking_id
    )

    if not matches:

        return {
            "status":
                "not_found",

            "message":
                "No active booking found.",
        }

    booking = matches[0]

    calendar_event_id = (
        booking.get(
            "calendar_event_id"
        )
    )

    if not calendar_event_id:

        return {
            "status":
                "error",

            "message":
                (
                    "Booking was found, but no "
                    "Calendar event ID is stored."
                ),
        }

    # ========================================================
    # 1. Check new availability
    #
    # IMPORTANT:
    # Ignore the booking's own Calendar event.
    # ========================================================

    try:

        available = is_slot_available(
            service_name=booking.get(
                "service"
            ),
            date_string=new_date,
            time_string=new_time,
            exclude_event_id=calendar_event_id,
        )

    except Exception as exc:

        print(
            "Reschedule availability error:",
            str(exc)
        )

        return {
            "status":
                "error",

            "message":
                "Could not check the new appointment time.",
        }

    if not available:

        return {
            "status":
                "unavailable",

            "message":
                "That new appointment time is not available.",
        }

    # ========================================================
    # 2. Prepare updated booking
    # ========================================================

    updated_booking = (
        booking.copy()
    )

    updated_booking[
        "date"
    ] = new_date

    updated_booking[
        "time"
    ] = new_time

    # ========================================================
    # 3. Update Google Calendar
    # ========================================================

    try:

        update_booking_event(
            calendar_event_id,
            updated_booking,
        )

    except Exception as exc:

        print(
            "Calendar reschedule error:",
            str(exc)
        )

        return {
            "status":
                "error",

            "message":
                "Could not update the Calendar event.",
        }

    # ========================================================
    # 4. Update Google Sheet
    # ========================================================

    try:

        update_booking_datetime(
            row_number=booking[
                "row_number"
            ],
            new_date=new_date,
            new_time=new_time,
        )

    except Exception as exc:

        print(
            "Sheet reschedule error:",
            str(exc)
        )

        return {
            "status":
                "partial_error",

            "message":
                (
                    "Calendar was updated, but the "
                    "Sheet could not be updated."
                ),
        }

    return {
        "status":
            "rescheduled",

        "booking":
            updated_booking,

        "message":
            (
                f"Booking {booking_id} "
                "has been rescheduled."
            ),
    }
