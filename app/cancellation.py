import re

from session_store import (
    get_session,
    save_session,
    delete_session,
)

from sheet_service import (
    find_bookings,
)

from cancellation_service import (
    cancel_booking_by_id,
)

from confirmation_utils import (
    normalize_confirmation_reply,
)


SESSION_TYPE = "cancellation"


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
#
# Examples accepted:
#
# 5232f7cb
# 5232 F7 CB
# 5 2 3 2 F 7 C B
# five two three two F seven C B
# فائیو ٹو تھری ٹو ایف سیون سی بی
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
    # 1. Normal continuous Booking ID
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
    # 2. Word-to-character map
    # ========================================================

    spoken_map = {

        # Digits - English
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


        # Digits - Roman Urdu
        "sifar": "0",
        "zeroo": "0",

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


        # Urdu-style English digit transcription
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


    # ========================================================
    # 3. Normalize punctuation
    # ========================================================

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

    characters = []


    # Words we do NOT want interpreted as hex.
    # Especially "a", because normal speech may contain
    # the English article "a".
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


    for token in tokens:

        token = token.strip().lower()

        if not token:
            continue

        if token in ignore_tokens:
            continue


        # Spoken number / letter
        if token in spoken_map:

            characters.append(
                spoken_map[token]
            )

            continue


        # Single numeric or hex character
        if re.fullmatch(
            r"[0-9a-f]",
            token,
        ):

            characters.append(
                token
            )

            continue


        # Chunk such as:
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
        f"Date: {date}\n"
        f"Time: {time}\n"
        f"Name: {name}"
    )


    if staff:

        text += (
            f"\nStaff: {staff}"
        )


    return text


# ============================================================
# Start cancellation
# ============================================================

def start_cancellation(
    user_id: str
):

    data = {
        "stage":
            "waiting_for_identifier",

        "bookings":
            [],

        "selected_booking":
            None,
    }


    save_session(
        user_id,
        SESSION_TYPE,
        data,
    )


    return (
        "Please provide your Booking ID "
        "or phone number used for the booking."
    )


# ============================================================
# Main cancellation workflow
# ============================================================

def handle_cancellation(
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

        return start_cancellation(
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


        booking_id = identifier.get(
            "booking_id"
        )

        phone = identifier.get(
            "phone"
        )


        print(
            "Cancellation identifier:",
            identifier,
        )


        if (
            not booking_id
            and not phone
        ):

            return (
                "I couldn't recognize the Booking ID. "
                "Please say the 8-character Booking ID "
                "slowly, for example: "
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
                "Cancellation lookup error:",
                repr(exc),
            )

            return (
                "I couldn't search your bookings "
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
                "waiting_for_confirmation"
            )


            save_session(
                user_id,
                SESSION_TYPE,
                data,
            )


            return (
                "I found this appointment:\n\n"
                f"{format_booking(selected)}\n\n"
                "Would you like to cancel it? "
                "Reply Yes or No."
            )


        # ====================================================
        # MULTIPLE BOOKINGS
        # ====================================================

        data[
            "bookings"
        ] = bookings

        data[
            "stage"
        ] = (
            "waiting_for_selection"
        )


        save_session(
            user_id,
            SESSION_TYPE,
            data,
        )


        lines = [
            "I found multiple active bookings. "
            "Please choose the appointment number "
            "you want to cancel:"
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
                "of the booking you want to cancel."
            )


        selection = int(
            match.group(0)
        )


        if (
            selection < 1
            or selection > len(bookings)
        ):

            return (
                "That booking number is not valid."
            )


        selected = (
            bookings[
                selection - 1
            ]
        )


        data[
            "selected_booking"
        ] = selected

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


        return (
            "You selected:\n\n"
            f"{format_booking(selected)}\n\n"
            "Would you like to cancel "
            "this appointment? "
            "Reply Yes or No."
        )


    # ========================================================
    # CONFIRMATION
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
                "Okay, your appointment "
                "has not been cancelled."
            )


        if answer != "yes":

            return (
                "Please confirm with Yes or No."
            )


        selected = data.get(
            "selected_booking"
        )


        if not selected:

            delete_session(
                user_id
            )

            return (
                "I couldn't find the selected booking. "
                "Please start again."
            )


        booking_id = booking_value(
            selected,
            "booking_id",
            "Booking_ID",
            "Booking ID",
        )


        try:

            result = cancel_booking_by_id(
                booking_id
            )


            print(
                "Cancellation result:",
                result,
            )


        except Exception as exc:

            print(
                "Cancellation error:",
                repr(exc),
            )

            return (
                "I couldn't cancel the appointment "
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
            "cancelled",
            "canceled",
            "success",
            "ok",
        }:

            delete_session(
                user_id
            )

            return (
                "Your appointment has been cancelled.\n\n"
                f"Booking ID: {booking_id}"
            )


        if status_text == "partial_error":

            delete_session(
                user_id
            )

            return (
                "The appointment was cancelled "
                "from the calendar, but there was "
                "a problem updating the booking record."
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
                "Your appointment has been cancelled.\n\n"
                f"Booking ID: {booking_id}"
            )


        return (
            "I couldn't cancel the appointment "
            "right now. Please try again."
        )


    delete_session(
        user_id
    )

    return start_cancellation(
        user_id
    )
