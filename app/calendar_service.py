import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from salon_config import (
    SALON_TIMEZONE,
    OPENING_TIME,
    CLOSING_TIME,
    SLOT_INTERVAL_MINUTES,
    SERVICE_CONFIG,
    TIME_WINDOWS,
)


GOOGLE_CALENDAR_CREDENTIALS = os.getenv(
    "GOOGLE_CALENDAR_CREDENTIALS"
)

GOOGLE_CALENDAR_ID = os.getenv(
    "GOOGLE_CALENDAR_ID"
)


# ============================================================
# Google Calendar connection
# ============================================================

def get_calendar_service():

    credentials = (
        service_account
        .Credentials
        .from_service_account_file(
            GOOGLE_CALENDAR_CREDENTIALS,
            scopes=[
                "https://www.googleapis.com/auth/calendar"
            ],
        )
    )

    return build(
        "calendar",
        "v3",
        credentials=credentials,
    )


# ============================================================
# Service duration
# ============================================================

def get_service_duration(
    service_name: str
):

    config = SERVICE_CONFIG.get(
        service_name
    )

    if not config:
        return None

    return config.get(
        "duration"
    )


# ============================================================
# Date helpers
# ============================================================

def get_day_bounds(
    date_string: str
):

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    date_value = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    day_start = datetime.combine(
        date_value,
        OPENING_TIME,
        tzinfo=timezone,
    )

    day_end = datetime.combine(
        date_value,
        CLOSING_TIME,
        tzinfo=timezone,
    )

    return (
        day_start,
        day_end,
    )


# ============================================================
# Time parser
# ============================================================

def parse_calendar_time(
    time_string: str
):

    if not time_string:
        return None

    value = (
        time_string
        .strip()
        .upper()
    )

    formats = [
        "%I:%M %p",   # 6:30 PM
        "%I %p",      # 6 PM
        "%I:%M%p",    # 6:30PM
        "%I%p",       # 6PM
        "%H:%M",      # 18:30
        "%H",         # 18
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt
            ).time()

        except ValueError:

            continue

    return None


def format_calendar_time(
    time_value
):

    return (
        datetime.combine(
            datetime.today(),
            time_value,
        )
        .strftime(
            "%I:%M %p"
        )
        .lstrip("0")
    )


# ============================================================
# Busy periods
# ============================================================

def get_busy_periods(
    date_string: str,
    exclude_event_id: str | None = None,
):

    service = get_calendar_service()

    day_start, day_end = (
        get_day_bounds(
            date_string
        )
    )

    result = (
        service
        .events()
        .list(
            calendarId=GOOGLE_CALENDAR_ID,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = result.get(
        "items",
        []
    )

    busy_periods = []

    for event in events:

        event_id = event.get(
            "id"
        )

        # Important for rescheduling:
        # ignore the appointment being moved.
        if (
            exclude_event_id
            and event_id == exclude_event_id
        ):
            continue

        start_value = (
            event
            .get(
                "start",
                {}
            )
            .get(
                "dateTime"
            )
        )

        end_value = (
            event
            .get(
                "end",
                {}
            )
            .get(
                "dateTime"
            )
        )

        # Ignore all-day events for now
        if (
            not start_value
            or not end_value
        ):
            continue

        start_dt = (
            datetime.fromisoformat(
                start_value.replace(
                    "Z",
                    "+00:00"
                )
            )
        )

        end_dt = (
            datetime.fromisoformat(
                end_value.replace(
                    "Z",
                    "+00:00"
                )
            )
        )

        busy_periods.append(
            {
                "start":
                    start_dt,

                "end":
                    end_dt,

                "event_id":
                    event_id,

                "summary":
                    event.get(
                        "summary",
                        ""
                    ),
            }
        )

    return busy_periods


# ============================================================
# Overlap
# ============================================================

def overlaps(
    start_a,
    end_a,
    start_b,
    end_b,
):

    return (
        start_a < end_b
        and end_a > start_b
    )


# ============================================================
# Exact slot availability
# ============================================================

def is_slot_available(
    service_name: str,
    date_string: str,
    time_string: str,
    exclude_event_id: str | None = None,
):

    duration = get_service_duration(
        service_name
    )

    if not duration:
        return False

    appointment_time = (
        parse_calendar_time(
            time_string
        )
    )

    if not appointment_time:

        print(
            "Could not parse appointment time:",
            time_string
        )

        return False

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    date_value = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    # Sunday closed
    if date_value.weekday() == 6:
        return False

    start_dt = datetime.combine(
        date_value,
        appointment_time,
        tzinfo=timezone,
    )

    end_dt = (
        start_dt
        + timedelta(
            minutes=duration
        )
    )

    opening_dt = datetime.combine(
        date_value,
        OPENING_TIME,
        tzinfo=timezone,
    )

    closing_dt = datetime.combine(
        date_value,
        CLOSING_TIME,
        tzinfo=timezone,
    )

    # Must start AND finish within salon hours
    if (
        start_dt < opening_dt
        or end_dt > closing_dt
    ):
        return False

    # Don't offer past times
    now = datetime.now(
        timezone
    )

    if start_dt <= now:
        return False

    busy_periods = get_busy_periods(
        date_string=date_string,
        exclude_event_id=exclude_event_id,
    )

    for busy in busy_periods:

        if overlaps(
            start_dt,
            end_dt,
            busy["start"],
            busy["end"],
        ):

            return False

    return True


# ============================================================
# Available slot list
# ============================================================

def get_available_slots(
    service_name: str,
    date_string: str,
    time_preference: str | None = None,
    exclude_event_id: str | None = None,
):

    duration = get_service_duration(
        service_name
    )

    if not duration:
        return []

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    date_value = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    # Sunday closed
    if date_value.weekday() == 6:
        return []

    # --------------------------------------------------------
    # Determine requested window
    # --------------------------------------------------------

    if (
        time_preference
        and time_preference in TIME_WINDOWS
    ):

        window_start_time, window_end_time = (
            TIME_WINDOWS[
                time_preference
            ]
        )

    else:

        window_start_time = (
            OPENING_TIME
        )

        window_end_time = (
            CLOSING_TIME
        )

    window_start = datetime.combine(
        date_value,
        window_start_time,
        tzinfo=timezone,
    )

    window_end = datetime.combine(
        date_value,
        window_end_time,
        tzinfo=timezone,
    )

    salon_close = datetime.combine(
        date_value,
        CLOSING_TIME,
        tzinfo=timezone,
    )

    busy_periods = get_busy_periods(
        date_string=date_string,
        exclude_event_id=exclude_event_id,
    )

    now = datetime.now(
        timezone
    )

    slots = []

    candidate_start = (
        window_start
    )

    while candidate_start < window_end:

        candidate_end = (
            candidate_start
            + timedelta(
                minutes=duration
            )
        )

        # Must finish before both:
        # selected window end and salon closing
        if (
            candidate_end > window_end
            or candidate_end > salon_close
        ):
            break

        # Ignore past slots
        if candidate_start <= now:

            candidate_start += timedelta(
                minutes=SLOT_INTERVAL_MINUTES
            )

            continue

        conflict = False

        for busy in busy_periods:

            if overlaps(
                candidate_start,
                candidate_end,
                busy["start"],
                busy["end"],
            ):

                conflict = True
                break

        if not conflict:

            slots.append(
                format_calendar_time(
                    candidate_start.time()
                )
            )

        candidate_start += timedelta(
            minutes=SLOT_INTERVAL_MINUTES
        )

    return slots


# ============================================================
# Create Calendar event
# ============================================================

def create_booking_event(
    booking_data: dict
):

    service_name = booking_data.get(
        "service"
    )

    date_string = booking_data.get(
        "date"
    )

    time_string = booking_data.get(
        "time"
    )

    customer_name = booking_data.get(
        "name"
    )

    staff = booking_data.get(
        "staff",
        ""
    )

    duration = get_service_duration(
        service_name
    )

    appointment_time = parse_calendar_time(
        time_string
    )

    if (
        not duration
        or not appointment_time
    ):

        raise ValueError(
            "Invalid booking service or time."
        )

    available = is_slot_available(
        service_name=service_name,
        date_string=date_string,
        time_string=time_string,
    )

    if not available:

        raise ValueError(
            "Requested Calendar slot is unavailable."
        )

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    date_value = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    start_dt = datetime.combine(
        date_value,
        appointment_time,
        tzinfo=timezone,
    )

    end_dt = start_dt + timedelta(
        minutes=duration
    )

    description_lines = [
        f"Customer: {customer_name}",
        f"Service: {service_name}",
        f"Staff: {staff}",
        f"Phone: {booking_data.get('phone', '')}",
        "Source: Salon AI Agent",
    ]

    event_body = {
        "summary":
            f"{service_name} - {customer_name}",

        "description":
            "\n".join(
                description_lines
            ),

        "start": {
            "dateTime":
                start_dt.isoformat(),

            "timeZone":
                SALON_TIMEZONE,
        },

        "end": {
            "dateTime":
                end_dt.isoformat(),

            "timeZone":
                SALON_TIMEZONE,
        },
    }

    service = get_calendar_service()

    event = (
        service
        .events()
        .insert(
            calendarId=GOOGLE_CALENDAR_ID,
            body=event_body,
        )
        .execute()
    )

    return {
        "event_id":
            event.get(
                "id"
            ),

        "html_link":
            event.get(
                "htmlLink"
            ),
    }


# ============================================================
# Delete Calendar event
# ============================================================

def delete_booking_event(
    event_id: str
):

    service = get_calendar_service()

    service.events().delete(
        calendarId=GOOGLE_CALENDAR_ID,
        eventId=event_id,
    ).execute()

    return True


# ============================================================
# Update Calendar event
# ============================================================

def update_booking_event(
    event_id: str,
    booking_data: dict
):

    service_name = booking_data.get(
        "service"
    )

    date_string = booking_data.get(
        "date"
    )

    time_string = booking_data.get(
        "time"
    )

    duration = get_service_duration(
        service_name
    )

    appointment_time = parse_calendar_time(
        time_string
    )

    if (
        not duration
        or not appointment_time
    ):

        raise ValueError(
            "Invalid service or appointment time."
        )

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    date_value = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    ).date()

    start_dt = datetime.combine(
        date_value,
        appointment_time,
        tzinfo=timezone,
    )

    end_dt = (
        start_dt
        + timedelta(
            minutes=duration
        )
    )

    # Retrieve existing event first
    service = get_calendar_service()

    event = (
        service
        .events()
        .get(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
        )
        .execute()
    )

    event["summary"] = (
        f"{service_name} - "
        f"{booking_data.get('name', '')}"
    )

    event["description"] = (
        f"Customer: {booking_data.get('name', '')}\n"
        f"Service: {service_name}\n"
        f"Staff: {booking_data.get('staff', '')}\n"
        f"Phone: {booking_data.get('phone', '')}\n"
        f"Source: Salon AI Agent"
    )

    event["start"] = {
        "dateTime":
            start_dt.isoformat(),

        "timeZone":
            SALON_TIMEZONE,
    }

    event["end"] = {
        "dateTime":
            end_dt.isoformat(),

        "timeZone":
            SALON_TIMEZONE,
    }

    updated = (
        service
        .events()
        .update(
            calendarId=GOOGLE_CALENDAR_ID,
            eventId=event_id,
            body=event,
        )
        .execute()
    )

    return {
        "event_id":
            updated.get(
                "id"
            ),

        "html_link":
            updated.get(
                "htmlLink"
            ),
    }
