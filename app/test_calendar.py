import os

from google.oauth2 import service_account
from googleapiclient.discovery import build


CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CALENDAR_CREDENTIALS"
)

CALENDAR_ID = os.getenv(
    "GOOGLE_CALENDAR_ID"
)


SCOPES = [
    "https://www.googleapis.com/auth/calendar"
]


def main():

    print(
        "Credentials:",
        bool(CREDENTIALS_FILE)
    )

    print(
        "Calendar ID:",
        bool(CALENDAR_ID)
    )

    credentials = (
        service_account.Credentials
        .from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )
    )

    service = build(
        "calendar",
        "v3",
        credentials=credentials
    )

    calendar = (
        service.calendars()
        .get(
            calendarId=CALENDAR_ID
        )
        .execute()
    )

    print(
        "Calendar connection successful"
    )

    print(
        "Calendar name:",
        calendar.get("summary")
    )


if __name__ == "__main__":
    main()
