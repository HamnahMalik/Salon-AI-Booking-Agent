import re
import json

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from openai import OpenAI

from session_store import (
    get_session,
    save_session,
    delete_session,
)

from salon_config import (
    SALON_TIMEZONE,
    SERVICE_CONFIG,
)

from calendar_service import (
    get_available_slots,
    is_slot_available,
    create_booking_event,
    delete_booking_event,
)

from sheet_service import (
    save_booking_to_sheet,
)

from confirmation_utils import (
    normalize_confirmation_reply,
)


client = OpenAI()

BOOKING_SESSION_TYPE = "booking"

REQUIRED_BOOKING_FIELDS = [
    "service",
    "date",
    "time",
    "name",
]


# ============================================================
# DEFAULT SESSION
# ============================================================

def default_booking_session():

    return {
        "service": None,
        "staff": None,
        "date": None,
        "time": None,
        "time_preference": None,
        "name": None,
        "phone": None,
        "stage": "collecting",
    }


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.lower() in {
        "none",
        "null",
        "unknown",
        "not provided",
        "n/a",
    }:
        return None

    return value


# ============================================================
# SERVICE NORMALIZATION
# ============================================================

def normalize_service(service):

    service = clean_text(service)

    if not service:
        return None

    value = service.lower().strip()

    aliases = {
        "haircut": "Haircut",
        "hair cut": "Haircut",
        "hair cutting": "Haircut",
        "cutting": "Haircut",
        "بال کٹوانا": "Haircut",

        "hair coloring": "Hair Coloring",
        "hair colouring": "Hair Coloring",
        "hair color": "Hair Coloring",
        "hair colour": "Hair Coloring",
        "coloring": "Hair Coloring",
        "colouring": "Hair Coloring",

        "facial": "Facial",
        "فیشل": "Facial",

        "manicure": "Manicure",
        "مینیکیور": "Manicure",

        "bridal": "Bridal Consultation",
        "bridal consultation": "Bridal Consultation",
        "bridal consult": "Bridal Consultation",
        "برائیڈل کنسلٹیشن": "Bridal Consultation",
    }

    if value in aliases:
        return aliases[value]

    for configured_service in SERVICE_CONFIG:

        if configured_service.lower() == value:
            return configured_service

    return None


# ============================================================
# STAFF NORMALIZATION
# ============================================================

def normalize_staff(staff):

    staff = clean_text(staff)

    if not staff:
        return None

    value = staff.lower().strip()

    for service_data in SERVICE_CONFIG.values():

        for staff_name in service_data.get(
            "staff",
            []
        ):

            if staff_name.lower() == value:
                return staff_name

    return None


# ============================================================
# TIME PARSER
# ============================================================

def parse_time_string(value):

    value = clean_text(value)

    if not value:
        return None

    text = value.strip().lower()

    replacements = {
        "baje": "",
        "bajy": "",
        "baja": "",
        "بجے": "",
        "o'clock": "",
        "oclock": "",
        "noon": "12 pm",
        "dopahar 12": "12 pm",
        "دوپہر 12": "12 pm",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    explicit_formats = [
        "%I:%M %p",
        "%I %p",
        "%I:%M%p",
        "%I%p",
    ]

    for fmt in explicit_formats:

        try:

            parsed = datetime.strptime(
                text.upper(),
                fmt,
            )

            return (
                parsed
                .strftime("%I:%M %p")
                .lstrip("0")
            )

        except ValueError:
            pass


    match = re.fullmatch(
        r"(\d{1,2}):(\d{2})",
        text,
    )

    if match:

        hour = int(match.group(1))
        minute = int(match.group(2))

        if not (
            0 <= hour <= 23
            and 0 <= minute <= 59
        ):
            return None

        if 1 <= hour <= 8:
            hour += 12

        parsed = datetime.strptime(
            f"{hour:02d}:{minute:02d}",
            "%H:%M",
        )

        return (
            parsed
            .strftime("%I:%M %p")
            .lstrip("0")
        )


    if re.fullmatch(
        r"\d{1,2}",
        text,
    ):

        hour = int(text)

        if 1 <= hour <= 8:
            hour += 12

        elif 9 <= hour <= 11:
            pass

        elif hour == 12:
            pass

        elif 13 <= hour <= 20:
            pass

        else:
            return None

        parsed = datetime.strptime(
            f"{hour:02d}:00",
            "%H:%M",
        )

        return (
            parsed
            .strftime("%I:%M %p")
            .lstrip("0")
        )

    return None


def format_time(value):

    return (
        parse_time_string(value)
        or value
    )


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_booking_date(value):

    value = clean_text(value)

    if not value:
        return None

    text = value.strip().lower()

    timezone = ZoneInfo(
        SALON_TIMEZONE
    )

    today = datetime.now(
        timezone
    ).date()


    if text in {
        "today",
        "aaj",
        "آج",
    }:

        return today.isoformat()


    if text in {
        "tomorrow",
        "kal",
        "کل",
    }:

        return (
            today
            + timedelta(days=1)
        ).isoformat()


    try:

        parsed = datetime.strptime(
            text,
            "%Y-%m-%d",
        )

        return parsed.strftime(
            "%Y-%m-%d"
        )

    except ValueError:
        pass


    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
    ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                value,
                fmt,
            )

            return parsed.strftime(
                "%Y-%m-%d"
            )

        except ValueError:
            pass

    return None


# ============================================================
# DISPLAY DATE
# ============================================================

def display_date(date_string):

    try:

        parsed = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        )

        return parsed.strftime(
            "%A, %d %B %Y"
        )

    except Exception:

        return date_string


# ============================================================
# ENGLISH STORAGE NAME
#
# Keeps conversation name unchanged,
# but stores Latin/English spelling in backend.
# ============================================================

def normalize_name_for_storage(name):

    name = clean_text(name)

    if not name:
        return ""

    # Already Latin/English-style text
    if re.fullmatch(
        r"[A-Za-z0-9 .'\-]+",
        name,
    ):
        return name.strip()

    prompt = f"""
Convert the following person's name into English Latin letters.

Rules:
- Transliterate the name only.
- Do not translate the meaning.
- Return ONLY the name.
- Do not add explanation.
- Do not add quotation marks.
- Preserve the natural pronunciation as closely as possible.
- If the text already contains an English spelling, preserve it.

Name:
{name}
"""

    try:

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        english_name = (
            response.output_text
            .strip()
            .strip('"')
            .strip("'")
        )

        if english_name:

            print(
                "Storage name normalized:",
                name,
                "->",
                english_name,
            )

            return english_name

    except Exception as exc:

        print(
            "Name transliteration error:",
            repr(exc),
        )

    # Safe fallback
    return name


# ============================================================
# LLM EXTRACTION
# ============================================================

def extract_booking_details(
    message: str,
    session=None,
):

    if session is None:
        session = {}

    now = datetime.now(
        ZoneInfo(SALON_TIMEZONE)
    )

    existing = {
        "service":
            session.get("service"),

        "staff":
            session.get("staff"),

        "date":
            session.get("date"),

        "time":
            session.get("time"),

        "time_preference":
            session.get("time_preference"),

        "name":
            session.get("name"),

        "phone":
            session.get("phone"),
    }

    prompt = f"""
You extract appointment booking information for
Glow & Grace Salon.

Current local datetime:
{now.strftime("%Y-%m-%d %H:%M")}

Timezone:
{SALON_TIMEZONE}

Services:
- Haircut
- Hair Coloring
- Facial
- Manicure
- Bridal Consultation

Staff:
- Sara
- Ayesha
- Hina

Existing booking information:

{json.dumps(existing, ensure_ascii=False)}

The customer can communicate in:
English,
Urdu,
Roman Urdu,
mixed Urdu/English,
or Hindi/Hinglish speech transcription.

Examples:

"kal facial karwana hai"
= Facial tomorrow

"sham 4 bajy"
= 4 PM

"مجھے کل فیشل بک کرنا ہے"
= Facial tomorrow

"haircut Safa ke liye"
= Haircut, customer name Safa

Rules:

- Extract only information given or clearly implied.
- Never invent details.
- Convert relative dates to YYYY-MM-DD.
- today/aaj/آج = today.
- tomorrow/kal/کل = tomorrow.
- 1-8 without AM/PM usually means PM.
- 9-11 without AM/PM usually means AM.
- 12 usually means noon.
- 13-20 can be 24-hour time.
- time_preference can be:
  morning,
  afternoon,
  evening.
- Never invent a customer name.
- Never invent a phone number.
- Preserve existing values unless the user clearly
  provides a replacement.

Return ONLY JSON:

{{
  "service": null,
  "staff": null,
  "date": null,
  "time": null,
  "time_preference": null,
  "name": null,
  "phone": null
}}

Current user message:

{message}
"""

    try:

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        result = json.loads(
            response.output_text.strip()
        )

        if isinstance(
            result,
            dict,
        ):
            return result

    except Exception as exc:

        print(
            "Booking extraction error:",
            repr(exc),
        )

    return {}


# ============================================================
# UPDATE SESSION
# ============================================================

def update_booking_session(
    user_id: str,
    message: str,
):

    existing = get_session(
        user_id
    )

    if (
        existing
        and existing.get(
            "session_type"
        )
        == BOOKING_SESSION_TYPE
    ):

        data = existing.get(
            "session_data",
            {}
        )

    else:

        data = (
            default_booking_session()
        )


    for key, value in (
        default_booking_session()
        .items()
    ):

        data.setdefault(
            key,
            value,
        )


    extracted = (
        extract_booking_details(
            message,
            data,
        )
    )


    if extracted.get(
        "service"
    ):

        service = normalize_service(
            extracted.get(
                "service"
            )
        )

        if service:

            old_service = data.get(
                "service"
            )

            data[
                "service"
            ] = service

            if (
                old_service
                and old_service
                != service
            ):

                valid_staff = (
                    SERVICE_CONFIG
                    .get(
                        service,
                        {}
                    )
                    .get(
                        "staff",
                        []
                    )
                )

                if (
                    data.get(
                        "staff"
                    )
                    not in valid_staff
                ):

                    data[
                        "staff"
                    ] = None


    if extracted.get(
        "staff"
    ):

        staff = normalize_staff(
            extracted.get(
                "staff"
            )
        )

        if staff:

            data[
                "staff"
            ] = staff


    if extracted.get(
        "date"
    ):

        date_value = (
            normalize_booking_date(
                extracted.get(
                    "date"
                )
            )
        )

        if date_value:

            data[
                "date"
            ] = date_value


    if extracted.get(
        "time"
    ):

        time_value = (
            parse_time_string(
                extracted.get(
                    "time"
                )
            )
        )

        if time_value:

            data[
                "time"
            ] = time_value


    if extracted.get(
        "time_preference"
    ):

        preference = (
            str(
                extracted.get(
                    "time_preference"
                )
            )
            .strip()
            .lower()
        )

        aliases = {
            "morning": "morning",
            "subah": "morning",
            "صبح": "morning",

            "afternoon": "afternoon",
            "dopahar": "afternoon",
            "دوپہر": "afternoon",

            "evening": "evening",
            "sham": "evening",
            "shaam": "evening",
            "شام": "evening",
        }

        if preference in aliases:

            data[
                "time_preference"
            ] = aliases[
                preference
            ]


    if extracted.get(
        "name"
    ):

        name = clean_text(
            extracted.get(
                "name"
            )
        )

        if name:

            data[
                "name"
            ] = name


    if extracted.get(
        "phone"
    ):

        phone = clean_text(
            extracted.get(
                "phone"
            )
        )

        if phone:

            data[
                "phone"
            ] = phone


    service = data.get(
        "service"
    )

    if service:

        staff_list = (
            SERVICE_CONFIG
            .get(
                service,
                {}
            )
            .get(
                "staff",
                []
            )
        )

        if (
            len(staff_list) == 1
            and not data.get(
                "staff"
            )
        ):

            data[
                "staff"
            ] = staff_list[0]


    data[
        "stage"
    ] = "collecting"


    save_session(
        user_id,
        BOOKING_SESSION_TYPE,
        data,
    )

    return data


# ============================================================
# MISSING FIELDS
# ============================================================

def get_missing_booking_fields(
    booking_data
):

    return [
        field
        for field
        in REQUIRED_BOOKING_FIELDS
        if not booking_data.get(field)
    ]


# ============================================================
# ASK FOR MISSING FIELD
# ============================================================

def ask_for_missing_booking_field(
    booking_data
):

    missing = (
        get_missing_booking_fields(
            booking_data
        )
    )

    if not missing:
        return None

    field = missing[0]


    if field == "service":

        return (
            "Which service would you like to book? "
            "We offer Haircut, Hair Coloring, Facial, "
            "Manicure, and Bridal Consultation."
        )


    if field == "date":

        return (
            "What date would you like "
            "your appointment?"
        )


    if field == "time":

        service = booking_data.get(
            "service"
        )

        date_string = booking_data.get(
            "date"
        )

        preference = booking_data.get(
            "time_preference"
        )

        if (
            service
            and date_string
        ):

            try:

                slots = get_available_slots(
                    service_name=service,
                    date_string=date_string,
                    time_preference=preference,
                )

                if slots:

                    return (
                        "What time would you prefer? "
                        "Available times include: "
                        + ", ".join(
                            slots[:8]
                        )
                    )

                return (
                    "There are no available slots "
                    "for that date. "
                    "Please choose another date."
                )

            except Exception as exc:

                print(
                    "Slot lookup error:",
                    repr(exc),
                )

        return (
            "What time would you prefer?"
        )


    if field == "name":

        return (
            "What name should I use "
            "for the booking?"
        )


    return (
        "Please provide the remaining "
        "appointment details."
    )


# ============================================================
# PREPARE CONFIRMATION
# ============================================================

def prepare_booking_confirmation(
    user_id: str,
    booking_data: dict,
):

    missing = (
        get_missing_booking_fields(
            booking_data
        )
    )

    if missing:

        return (
            ask_for_missing_booking_field(
                booking_data
            )
        )


    service = booking_data.get(
        "service"
    )

    date_string = booking_data.get(
        "date"
    )

    time_string = booking_data.get(
        "time"
    )


    try:

        available = is_slot_available(
            service_name=service,
            date_string=date_string,
            time_string=time_string,
        )

    except Exception as exc:

        print(
            "Availability error:",
            repr(exc),
        )

        return (
            "I couldn't check availability "
            "right now. Please try again."
        )


    if not available:

        booking_data[
            "time"
        ] = None

        booking_data[
            "stage"
        ] = "collecting"

        save_session(
            user_id,
            BOOKING_SESSION_TYPE,
            booking_data,
        )


        try:

            slots = get_available_slots(
                service_name=service,
                date_string=date_string,
                time_preference=booking_data.get(
                    "time_preference"
                ),
            )

        except Exception:

            slots = []


        if slots:

            return (
                f"{time_string} is not available. "
                "Available times include: "
                + ", ".join(
                    slots[:8]
                )
                + ". Please choose another time."
            )


        return (
            "That time is not available. "
            "Please choose another date or time."
        )


    booking_data[
        "stage"
    ] = "waiting_for_confirmation"


    save_session(
        user_id,
        BOOKING_SESSION_TYPE,
        booking_data,
    )


    reply = (
        "Please confirm your appointment details:\n\n"
        f"Service: {service}\n"
        f"Date: {display_date(date_string)}\n"
        f"Time: {time_string}\n"
        f"Name: {booking_data.get('name')}"
    )


    if booking_data.get(
        "staff"
    ):

        reply += (
            "\nStaff: "
            + booking_data.get(
                "staff"
            )
        )


    reply += (
        "\n\nReply Yes to confirm "
        "or No to cancel."
    )

    return reply


# ============================================================
# HANDLE CONFIRMATION
# ============================================================

def handle_booking_confirmation(
    user_id: str,
    user_text: str,
):

    session = get_session(
        user_id
    )


    if (
        not session
        or session.get(
            "session_type"
        )
        != BOOKING_SESSION_TYPE
    ):

        return (
            "There is no booking waiting "
            "for confirmation."
        )


    booking_data = session.get(
        "session_data",
        {}
    )


    if (
        booking_data.get(
            "stage"
        )
        != "waiting_for_confirmation"
    ):

        return (
            "Your booking is not ready "
            "for confirmation yet."
        )


    answer = normalize_confirmation_reply(
        user_text
    )


    print(
        "Booking confirmation normalized:",
        answer,
    )


    if answer == "no":

        delete_session(
            user_id
        )

        return (
            "Okay, the appointment "
            "was not booked."
        )


    if answer != "yes":

        return (
            "Please confirm the appointment "
            "with Yes or No."
        )


    service = booking_data.get(
        "service"
    )

    date_string = booking_data.get(
        "date"
    )

    time_string = booking_data.get(
        "time"
    )

    original_name = booking_data.get(
        "name"
    )

    staff = booking_data.get(
        "staff"
    )

    phone = booking_data.get(
        "phone"
    )


    # ========================================================
    # Convert customer name to English for storage only
    # ========================================================

    storage_name = (
        normalize_name_for_storage(
            original_name
        )
    )


    print(
        "Original name:",
        original_name,
    )

    print(
        "Stored English name:",
        storage_name,
    )


    # ========================================================
    # FINAL AVAILABILITY CHECK
    # ========================================================

    try:

        available = is_slot_available(
            service_name=service,
            date_string=date_string,
            time_string=time_string,
        )

    except Exception as exc:

        print(
            "Final availability error:",
            repr(exc),
        )

        return (
            "I couldn't confirm availability "
            "right now. Please try again."
        )


    if not available:

        booking_data[
            "time"
        ] = None

        booking_data[
            "stage"
        ] = "collecting"

        save_session(
            user_id,
            BOOKING_SESSION_TYPE,
            booking_data,
        )


        try:

            slots = get_available_slots(
                service_name=service,
                date_string=date_string,
                time_preference=booking_data.get(
                    "time_preference"
                ),
            )

        except Exception:

            slots = []


        if slots:

            return (
                "That time has just become unavailable. "
                "Please choose another time. "
                "Available times include: "
                + ", ".join(
                    slots[:8]
                )
            )


        return (
            "That appointment time is no longer "
            "available. Please choose another time."
        )


    # ========================================================
    # CALENDAR
    #
    # Store name in English.
    # ========================================================

    calendar_booking_data = {
        "name":
            storage_name,

        "phone":
            phone or "",

        "service":
            service,

        "staff":
            staff or "",

        "date":
            date_string,

        "time":
            time_string,
    }


    try:

        print(
            "Sending booking to Calendar:",
            calendar_booking_data,
        )


        calendar_result = (
            create_booking_event(
                calendar_booking_data
            )
        )


        print(
            "Calendar create result:",
            calendar_result,
        )


        calendar_event_id = (
            calendar_result.get(
                "event_id"
            )
            if isinstance(
                calendar_result,
                dict,
            )
            else None
        )


        if not calendar_event_id:

            raise RuntimeError(
                "Calendar Event ID "
                "was not returned."
            )


    except Exception as exc:

        print(
            "Calendar booking error:",
            repr(exc),
        )

        return (
            "I couldn't create the appointment "
            "in the calendar. Please try again."
        )


    # ========================================================
    # GOOGLE SHEET
    #
    # Store name in English.
    # ========================================================

    sheet_booking_data = {
        "name":
            storage_name,

        "phone":
            phone or "",

        "service":
            service,

        "staff":
            staff or "",

        "date":
            date_string,

        "time":
            time_string,

        "calendar_event_id":
            calendar_event_id,
    }


    try:

        print(
            "Sending booking to Sheet:",
            sheet_booking_data,
        )


        sheet_result = (
            save_booking_to_sheet(
                sheet_booking_data
            )
        )


        print(
            "Sheet save result:",
            sheet_result,
        )


        if not isinstance(
            sheet_result,
            dict,
        ):

            raise RuntimeError(
                "Sheet did not return "
                "booking information."
            )


        booking_id = sheet_result.get(
            "booking_id"
        )


        if not booking_id:

            raise RuntimeError(
                "Sheet did not return "
                "a Booking ID."
            )


    except Exception as exc:

        print(
            "Sheet save error:",
            repr(exc),
        )


        # Roll back Calendar event if Sheet fails

        try:

            delete_booking_event(
                calendar_event_id
            )


            print(
                "Calendar rollback completed:",
                calendar_event_id,
            )


        except Exception as rollback_exc:

            print(
                "Calendar rollback error:",
                repr(
                    rollback_exc
                ),
            )


        return (
            "I couldn't save the booking completely. "
            "Please try again."
        )


    # ========================================================
    # SUCCESS
    # ========================================================

    delete_session(
        user_id
    )


    # Customer-facing reply can still use the original
    # Urdu/Roman Urdu name. The localization layer will
    # translate the rest of this reply.

    confirmation = (
        "Your appointment has been confirmed.\n\n"
        f"Booking ID: {booking_id}\n"
        f"Service: {service}\n"
        f"Date: {display_date(date_string)}\n"
        f"Time: {time_string}\n"
        f"Name: {original_name}"
    )


    if staff:

        confirmation += (
            f"\nStaff: {staff}"
        )


    return confirmation
