import re

from datetime import datetime

from session_store import (
    get_session,
    save_session,
    delete_session,
)

from sheet_service import (
    find_bookings,
)

from calendar_service import (
    get_available_slots,
    is_slot_available,
)

from reschedule_service import (
    reschedule_booking,
)

from booking import (
    extract_booking_details,
    normalize_booking_date,
    parse_time_string,
    format_time,
)

from confirmation_utils import (
    normalize_confirmation_reply,
)


SESSION_TYPE = "reschedule"


# ============================================================
# Generic booking value helper
# ============================================================

def booking_value(
    booking: dict,
    *keys,
):

    for key in keys:

        if key in booking:

            value = booking.get(
                key
            )

            if value not in (
                None,
                "",
            ):
                return value

    return None


# ============================================================
# VOICE-AWARE BOOKING ID NORMALIZATION
# ============================================================

def normalize_spoken_booking_id(
    text: str
):

    if not text:
        return None


    original = (
        str(text)
        .strip()
        .lower()
    )


    # ========================================================
    # Normal typed/continuous ID
    # ========================================================

    direct_match = re.search(
        r"\b[0-9a-f]{8}\b",
        original,
        flags=re.IGNORECASE,
    )


    if direct_match:

        return (
            direct_match
            .group(0)
            .lower()
        )


    # ========================================================
    # Spoken token map
    # ========================================================

    spoken_map = {

        # English digits
        "zero": "0",
        "oh": "0",
        "o": "0",

        "one": "1",
        "won": "1",

        "two": "2",
        "to": "2",
        "too": "2",

        "three": "3",

        "four": "4",
        "for": "4",

        "five": "5",

        "six": "6",

        "seven": "7",

        "eight": "8",
        "ate": "8",

        "nine": "9",


        # Roman Urdu numbers
        "sifar": "0",

        "aik": "1",
        "ek": "1",

        "do": "2",

        "teen": "3",

        "char": "4",
        "chaar": "4",

        "panch": "5",
        "paanch": "5",

        "che": "6",
        "chay": "6",

        "saat": "7",

        "aath": "8",

        "nau": "9",


        # Urdu STT forms
        "زیرو": "0",
        "ون": "1",
        "ٹو": "2",
        "تھری": "3",
        "فور": "4",
        "فائیو": "5",
        "فایو": "5",
        "سکس": "6",
        "سیون": "7",
        "ایٹ": "8",
        "نائن": "9",


        # Hex letters
        "ay": "a",
        "اے": "a",

        "bee": "b",
        "بی": "b",

        "see": "c",
        "سی": "c",

        "dee": "d",
        "ڈی": "d",

        "ee": "e",
        "ای": "e",

        "eff": "f",
        "ef": "f",
        "ایف": "f",
    }


    cleaned = re.sub(
        r"[,.:;_\-/\\|]+",
        " ",
        original,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()


    tokens = cleaned.split()


    ignore_tokens = {
        "booking",
        "book",
        "id",
        "number",
        "code",
        "is",
        "the",
        "my",
        "mera",
        "meri",
        "hai",
        "he",
        "ka",
        "ki",
        "please",
        "appointment",
        "reference",
        "ref",
        "a",
        "and",

        "ہے",
        "میری",
        "میرا",
        "بکنگ",
        "آئی",
        "ڈی",
        "نمبر",
    }


    characters = []


    for token in tokens:

        token = token.strip().lower()


        if not token:
            continue


        if token in ignore_tokens:
            continue


        if token in spoken_map:

            characters.append(
                spoken_map[token]
            )

            continue


        if re.fullmatch(
            r"[0-9a-f]",
            token,
        ):

            characters.append(
                token
            )

            continue


        # Handles chunks such as:
        # 5232
        # f7
        # cb

        if re.fullmatch(
            r"[0-9a-f]+",
            token,
        ):

            characters.extend(
                list(token)
            )

            continue


    candidate = "".join(
        characters
    ).lower()


    if re.fullmatch(
        r"[0-9a-f]{8}",
        candidate,
    ):

        print(
            "Voice Booking ID normalized:",
            text,
            "->",
            candidate,
        )

        return candidate


    print(
        "Unable to normalize Booking ID:",
        text,
        "Candidate:",
        candidate,
    )

    return None


# ============================================================
# Phone extraction
# ============================================================

def extract_phone(
    text
):

    if not text:
        return None


    digits = re.sub(
        r"\D",
        "",
        str(text),
    )


    if len(digits) >= 7:
        return digits


    return None


# ============================================================
# Identifier extraction
# ============================================================

def extract_identifier(
    message: str
):

    booking_id = (
        normalize_spoken_booking_id(
            message
        )
    )


    if booking_id:

        return {
            "booking_id":
                booking_id,

            "phone":
                None,
        }


    phone = extract_phone(
        message
    )


    if phone:

        return {
            "booking_id":
                None,

            "phone":
                phone,
        }


    return {
        "booking_id":
            None,

        "phone":
            None,
    }


# ============================================================
# Date display
# ============================================================

def display_date(
    value
):

    try:

        return (
            datetime.strptime(
                value,
                "%Y-%m-%d",
            )
            .strftime(
                "%A, %d %B %Y"
            )
        )

    except Exception:

        return value


# ============================================================
# Format booking
# ============================================================

def format_booking(
    booking: dict,
    index=None,
):

    booking_id = booking_value(
        booking,
        "booking_id",
        "Booking_ID",
        "Booking ID",
    )

    service = booking_value(
        booking,
        "service",
        "Service",
    )

    date = booking_value(
        booking,
        "date",
        "Date",
    )

    time = booking_value(
        booking,
        "time",
        "Time",
    )

    name = booking_value(
        booking,
        "name",
        "Name",
    )

    staff = booking_value(
        booking,
        "staff",
        "Staff",
    )


    prefix = ""

    if index is not None:

        prefix = (
            f"{index}. "
        )


    text = (
        f"{prefix}"
        f"Booking ID: {booking_id}\n"
        f"Service: {service}\n"
        f"Date: {display_date(date)}\n"
        f"Time: {time}\n"
        f"Name: {name}"
    )


    if staff:

        text += (
            f"\nStaff: {staff}"
        )


    return text


# ============================================================
# Start rescheduling
# ============================================================

def start_reschedule(
    user_id: str
):

    data = {
        "stage":
            "waiting_for_identifier",

        "bookings":
            [],

        "selected_booking":
            None,

        "new_date":
            None,

        "new_time":
            None,

        "time_preference":
            None,
    }


    save_session(
        user_id,
        SESSION_TYPE,
        data,
    )


    return (
        "Please provide your Booking ID "
        "or phone number used for the appointment."
    )


# ============================================================
# Main reschedule flow
# ============================================================

def handle_reschedule(
    user_id: str,
    message: str,
):

    session = get_session(
        user_id
    )


    if (
        not session
        or session.get(
            "session_type"
        )
        != SESSION_TYPE
    ):

        return start_reschedule(
            user_id
        )


    data = session.get(
        "session_data",
        {}
    )


    stage = data.get(
        "stage",
        "waiting_for_identifier",
    )


    # ========================================================
    # IDENTIFIER
    # ========================================================

    if stage == "waiting_for_identifier":

        identifier = (
            extract_identifier(
                message
            )
        )


        print(
            "Reschedule identifier:",
            identifier,
        )


        booking_id = identifier.get(
            "booking_id"
        )

        phone = identifier.get(
            "phone"
        )


        if (
            not booking_id
            and not phone
        ):

            return (
                "I couldn't recognize the Booking ID. "
                "Please say the 8-character ID slowly, "
                "for example: "
                "'five two three two F seven C B', "
                "or provide your phone number."
            )


        try:

            if booking_id:

                bookings = find_bookings(
                    booking_id=booking_id
                )

            else:

                bookings = find_bookings(
                    phone=phone
                )


        except Exception as exc:

            print(
                "Reschedule lookup error:",
                repr(exc),
            )

            return (
                "I couldn't search your appointments "
                "right now. Please try again."
            )


        if not bookings:

            return (
                "I couldn't find an active booking "
                "with those details."
            )


        # ====================================================
        # ONE BOOKING
        # ====================================================

        if len(bookings) == 1:

            selected = bookings[0]


            data[
                "selected_booking"
            ] = selected

            data[
                "stage"
            ] = (
                "waiting_for_new_date"
            )


            save_session(
                user_id,
                SESSION_TYPE,
                data,
            )


            return (
                "I found this appointment:\n\n"
                f"{format_booking(selected)}\n\n"
                "What new date would you like?"
            )


        # ====================================================
        # MULTIPLE BOOKINGS
        # ====================================================

        data[
            "bookings"
        ] = bookings

        data[
            "stage"
        ] = "waiting_for_selection"


        save_session(
            user_id,
            SESSION_TYPE,
            data,
        )


        lines = [
            "I found multiple active bookings. "
            "Please choose the appointment number "
            "you want to reschedule:"
        ]


        for index, booking in enumerate(
            bookings,
            start=1,
        ):

            lines.append(
                "\n"
                + format_booking(
                    booking,
                    index,
                )
            )


        return "\n".join(
            lines
        )


    # ========================================================
    # SELECT BOOKING
    # ========================================================

    if stage == "waiting_for_selection":

        bookings = data.get(
            "bookings",
            []
        )


        match = re.search(
            r"\d+",
            str(message),
        )


        if not match:

            return (
                "Please say or enter the number "
                "of the appointment you want "
                "to reschedule."
            )


        selection = int(
            match.group(0)
        )


        if (
            selection < 1
            or selection > len(bookings)
        ):

            return (
                "That appointment number "
                "is not valid."
            )


        selected = bookings[
            selection - 1
        ]


        data[
            "selected_booking"
        ] = selected

        data[
            "stage"
        ] = "waiting_for_new_date"


        save_session(
            user_id,
            SESSION_TYPE,
            data,
        )


        return (
            "You selected:\n\n"
            f"{format_booking(selected)}\n\n"
            "What new date would you like?"
        )


    # ========================================================
    # NEW DATE
    # ========================================================

    if stage == "waiting_for_new_date":

        selected = data.get(
            "selected_booking",
            {}
        )


        current_date = booking_value(
            selected,
            "date",
            "Date",
        )


        text = (
            str(message)
            .strip()
            .lower()
        )


        if text in {
            "same",
            "same day",
            "same date",
            "usi din",
            "ussi din",
            "us din",
            "اسی دن",
            "اسی تاریخ",
        }:

            new_date = current_date


        else:

            new_date = (
                normalize_booking_date(
                    message
                )
            )


        # ====================================================
        # Natural language date backup
        # ====================================================

        if not new_date:

            try:

                extracted = (
                    extract_booking_details(
                        message,
                        session={
                            "date": None,
                        },
                    )
                )


                extracted_date = (
                    extracted.get(
                        "date"
                    )
                    if isinstance(
                        extracted,
                        dict,
                    )
                    else None
                )


                if extracted_date:

                    new_date = (
                        normalize_booking_date(
                            extracted_date
                        )
                    )


            except Exception as exc:

                print(
                    "Date extraction error:",
                    repr(exc),
                )


        if not new_date:

            return (
                "I couldn't understand the new date. "
                "Please say a date such as "
                "'tomorrow', '20 October', "
                "or 'same day'."
            )


        data[
            "new_date"
        ] = new_date

        data[
            "new_time"
        ] = None

        data[
            "stage"
        ] = "waiting_for_new_time"


        save_session(
            user_id,
            SESSION_TYPE,
            data,
        )


        service = booking_value(
            selected,
            "service",
            "Service",
        )


        calendar_event_id = booking_value(
            selected,
            "calendar_event_id",
            "Calendar_Event_ID",
            "Calendar Event ID",
        )


        try:

            slots = get_available_slots(
                service_name=service,
                date_string=new_date,
                time_preference=None,
                exclude_event_id=calendar_event_id,
            )


        except Exception as exc:

            print(
                "Reschedule slot error:",
                repr(exc),
            )

            slots = []


        if slots:

            return (
                f"What new time would you like on "
                f"{display_date(new_date)}?\n\n"
                "Available times include: "
                + ", ".join(
                    slots[:8]
                )
            )


        return (
            f"What new time would you like on "
            f"{display_date(new_date)}?"
        )


    # ========================================================
    # NEW TIME
    # ========================================================

    if stage == "waiting_for_new_time":

        selected = data.get(
            "selected_booking",
            {}
        )


        service = booking_value(
            selected,
            "service",
            "Service",
        )


        calendar_event_id = booking_value(
            selected,
            "calendar_event_id",
            "Calendar_Event_ID",
            "Calendar Event ID",
        )


        new_date = data.get(
            "new_date"
        )


        new_time = (
            parse_time_string(
                message
            )
        )


        preference = None


        if not new_time:

            try:

                extracted = (
                    extract_booking_details(
                        message,
                        session={
                            "service":
                                service,

                            "date":
                                new_date,
                        },
                    )
                )


                if isinstance(
                    extracted,
                    dict,
                ):

                    if extracted.get(
                        "time"
                    ):

                        new_time = (
                            parse_time_string(
                                extracted.get(
                                    "time"
                                )
                            )
                        )


                    preference = (
                        extracted.get(
                            "time_preference"
                        )
                    )


            except Exception as exc:

                print(
                    "Time extraction error:",
                    repr(exc),
                )


        # ====================================================
        # Preference only
        # ====================================================

        if (
            not new_time
            and preference
        ):

            preference = (
                str(preference)
                .strip()
                .lower()
            )


            data[
                "time_preference"
            ] = preference


            save_session(
                user_id,
                SESSION_TYPE,
                data,
            )


            try:

                slots = get_available_slots(
                    service_name=service,
                    date_string=new_date,
                    time_preference=preference,
                    exclude_event_id=calendar_event_id,
                )


            except Exception as exc:

                print(
                    "Preference slot error:",
                    repr(exc),
                )

                slots = []


            if slots:

                return (
                    f"Available {preference} times are: "
                    + ", ".join(
                        slots[:8]
                    )
                    + ". Which one would you like?"
                )


            return (
                f"There are no available "
                f"{preference} slots. "
                "Please choose another time."
            )


        if not new_time:

            return (
                "I couldn't understand the new time. "
                "Please say a time such as "
                "'3 PM', 'sham 4 baje', "
                "or '18:30'."
            )


        new_time = format_time(
            new_time
        )


        # ====================================================
        # Availability check excluding current event
        # ====================================================

        try:

            available = is_slot_available(
                service_name=service,
                date_string=new_date,
                time_string=new_time,
                exclude_event_id=calendar_event_id,
            )


        except Exception as exc:

            print(
                "Reschedule availability error:",
                repr(exc),
            )

            return (
                "I couldn't check that time "
                "right now. Please try again."
            )


        if not available:

            try:

                slots = get_available_slots(
                    service_name=service,
                    date_string=new_date,
                    time_preference=data.get(
                        "time_preference"
                    ),
                    exclude_event_id=calendar_event_id,
                )


            except Exception:

                slots = []


            if slots:

                return (
                    f"{new_time} is not available. "
                    "Available times include: "
                    + ", ".join(
                        slots[:8]
                    )
                )


            return (
                "That time is not available. "
                "Please choose another time."
            )


        data[
            "new_time"
        ] = new_time

        data[
            "stage"
        ] = (
            "waiting_for_confirmation"
        )


        save_session(
            user_id,
            SESSION_TYPE,
            data,
        )


        booking_id = booking_value(
            selected,
            "booking_id",
            "Booking_ID",
            "Booking ID",
        )


        return (
            "Please confirm the reschedule:\n\n"
            f"Booking ID: {booking_id}\n"
            f"Service: {service}\n"
            f"New Date: {display_date(new_date)}\n"
            f"New Time: {new_time}\n\n"
            "Reply Yes to confirm or No to cancel."
        )


    # ========================================================
    # CONFIRM RESCHEDULE
    # ========================================================

    if stage == "waiting_for_confirmation":

        answer = (
            normalize_confirmation_reply(
                message
            )
        )


        if answer == "no":

            delete_session(
                user_id
            )

            return (
                "Okay, the appointment "
                "was not rescheduled."
            )


        if answer != "yes":

            return (
                "Please confirm the reschedule "
                "with Yes or No."
            )


        selected = data.get(
            "selected_booking",
            {}
        )


        booking_id = booking_value(
            selected,
            "booking_id",
            "Booking_ID",
            "Booking ID",
        )


        new_date = data.get(
            "new_date"
        )

        new_time = data.get(
            "new_time"
        )


        if (
            not booking_id
            or not new_date
            or not new_time
        ):

            delete_session(
                user_id
            )

            return (
                "Some rescheduling information "
                "is missing. Please start again."
            )


        try:

            result = reschedule_booking(
                booking_id,
                new_date,
                new_time,
            )


            print(
                "Reschedule result:",
                result,
            )


        except Exception as exc:

            print(
                "Reschedule backend error:",
                repr(exc),
            )

            return (
                "I couldn't reschedule the appointment "
                "right now. Please try again."
            )


        status = None


        if isinstance(
            result,
            dict,
        ):

            status = (
                result.get("status")
                or result.get("result")
            )


        elif isinstance(
            result,
            str,
        ):

            status = result


        status_text = (
            str(status or "")
            .strip()
            .lower()
        )


        if status_text in {
            "rescheduled",
            "success",
            "ok",
            "updated",
        }:

            delete_session(
                user_id
            )

            return (
                "Your appointment has been rescheduled.\n\n"
                f"Booking ID: {booking_id}\n"
                f"New Date: {display_date(new_date)}\n"
                f"New Time: {new_time}"
            )


        if status_text == "unavailable":

            data[
                "new_time"
            ] = None

            data[
                "stage"
            ] = (
                "waiting_for_new_time"
            )


            save_session(
                user_id,
                SESSION_TYPE,
                data,
            )


            return (
                "That time is no longer available. "
                "Please choose another time."
            )


        if status_text == "partial_error":

            delete_session(
                user_id
            )

            return (
                "The Calendar appointment was changed, "
                "but there was a problem updating "
                "the booking record."
            )


        if status_text in {
            "not_found",
            "not found",
        }:

            delete_session(
                user_id
            )

            return (
                "That active booking could "
                "not be found."
            )


        if result:

            delete_session(
                user_id
            )

            return (
                "Your appointment has been rescheduled.\n\n"
                f"Booking ID: {booking_id}\n"
                f"New Date: {display_date(new_date)}\n"
                f"New Time: {new_time}"
            )


        return (
            "I couldn't reschedule the appointment "
            "right now. Please try again."
        )


    delete_session(
        user_id
    )

    return start_reschedule(
        user_id
    )
