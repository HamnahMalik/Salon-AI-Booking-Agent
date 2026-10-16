import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build

from salon_config import SALON_TIMEZONE, SERVICE_CONFIG


GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS")


def get_sheets_service():
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )

    return build(
        "sheets",
        "v4",
        credentials=credentials,
    )


def get_service_duration(service_name: str):
    config = SERVICE_CONFIG.get(service_name)

    if not config:
        return ""

    return config.get("duration", "")


# ============================================================
# SAVE BOOKING
# ============================================================

def save_booking_to_sheet(booking_data: dict):
    service = get_sheets_service()

    booking_id = str(uuid.uuid4())[:8]

    created_at = datetime.now(
        ZoneInfo(SALON_TIMEZONE)
    ).isoformat()

    row = [[
        booking_id,
        booking_data.get("name", ""),
        booking_data.get("phone", ""),
        booking_data.get("service", ""),
        booking_data.get("staff", ""),
        booking_data.get("date", ""),
        booking_data.get("time", ""),
        get_service_duration(
            booking_data.get("service")
        ),
        "Confirmed",
        booking_data.get("calendar_event_id", ""),
        "WhatsApp",
        created_at,
    ]]

    result = (
        service
        .spreadsheets()
        .values()
        .append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="A:L",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        )
        .execute()
    )

    return {
        "booking_id": booking_id,
        "updated_range": result.get(
            "updates",
            {}
        ).get(
            "updatedRange"
        ),
    }


# ============================================================
# GET ALL BOOKINGS
# ============================================================

def get_all_bookings():
    service = get_sheets_service()

    result = (
        service
        .spreadsheets()
        .values()
        .get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="A2:L",
        )
        .execute()
    )

    rows = result.get(
        "values",
        []
    )

    bookings = []

    for index, row in enumerate(
        rows,
        start=2
    ):
        padded = row + [""] * (
            12 - len(row)
        )

        booking = {
            "row_number": index,
            "booking_id": padded[0],
            "name": padded[1],
            "phone": padded[2],
            "service": padded[3],
            "staff": padded[4],
            "date": padded[5],
            "time": padded[6],
            "duration": padded[7],
            "status": padded[8],
            "calendar_event_id": padded[9],
            "source": padded[10],
            "created_at": padded[11],
        }

        bookings.append(
            booking
        )

    return bookings


# ============================================================
# FIND BOOKING
# ============================================================

def find_bookings(
    booking_id=None,
    phone=None
):
    bookings = get_all_bookings()

    matches = []

    for booking in bookings:

        # Only active bookings
        if (
            booking.get("status", "")
            .strip()
            .lower()
            != "confirmed"
        ):
            continue

        if booking_id:

            if (
                booking.get(
                    "booking_id",
                    ""
                ).strip().lower()
                == booking_id.strip().lower()
            ):
                matches.append(
                    booking
                )

        elif phone:

            sheet_phone = (
                booking.get(
                    "phone",
                    ""
                )
                .replace(" ", "")
                .replace("-", "")
            )

            search_phone = (
                phone
                .replace(" ", "")
                .replace("-", "")
            )

            if (
                sheet_phone
                == search_phone
            ):
                matches.append(
                    booking
                )

    return matches


# ============================================================
# UPDATE STATUS
# ============================================================

def update_booking_status(
    row_number: int,
    status: str
):
    service = get_sheets_service()

    range_name = (
        f"I{row_number}"
    )

    service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={
            "values": [
                [status]
            ]
        },
    ).execute()

    return True

def update_booking_datetime(
    row_number: int,
    new_date: str,
    new_time: str
):
    service = get_sheets_service()

    service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"F{row_number}:G{row_number}",
        valueInputOption="USER_ENTERED",
        body={
            "values": [[
                new_date,
                new_time,
            ]]
        },
    ).execute()

    return True
