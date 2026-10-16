import json
import re

from openai import OpenAI

from language_store import (
    get_user_language,
    save_user_language,
)


client = OpenAI()


VALID_STYLES = {
    "english",
    "urdu",
    "roman_urdu",
    "mixed",
}


# ============================================================
# Helpers
# ============================================================

def contains_urdu_script(
    text: str
):
    return bool(
        re.search(
            r"[\u0600-\u06FF]",
            text or "",
        )
    )


def is_short_ambiguous_message(
    message: str
):
    """
    Messages such as:
    yes
    no
    okay
    Ayera
    2 PM

    should normally inherit the existing
    conversation language.
    """

    text = (
        message or ""
    ).strip()

    if not text:
        return True

    # Urdu script is not ambiguous.
    if contains_urdu_script(
        text
    ):
        return False

    words = text.split()

    # Common confirmation / conversational words
    ambiguous_words = {
        "yes",
        "y",
        "no",
        "n",
        "ok",
        "okay",
        "sure",
        "confirm",
        "confirmed",
        "cancel",
        "stop",
        "thanks",
        "thankyou",
        "thank",
    }

    if text.lower() in ambiguous_words:
        return True

    # A single name, number or time should not
    # change the conversation language.
    if len(words) <= 2:
        return True

    return False


# ============================================================
# Detect language style
# ============================================================

def detect_language_style(
    message: str
):

    prompt = f"""
Classify the language style of this salon customer message.

Return exactly one of:

english
urdu
roman_urdu
mixed

Definitions:

english:
Mostly English.

urdu:
Mostly Urdu written in Urdu script.

roman_urdu:
Mostly Urdu written using Latin/English letters.

mixed:
A meaningful mixture of English and Roman Urdu.

Examples:

"book a facial tomorrow"
-> english

"مجھے کل فیشل بک کرنا ہے"
-> urdu

"mein ny booking karwani hai"
-> roman_urdu

"kal facial book karni hai"
-> roman_urdu

"Can you kal 3 baje haircut book kar dein?"
-> mixed

Message:

{message}

Return ONLY JSON:

{{
  "language_style": "roman_urdu"
}}
"""

    try:

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        data = json.loads(
            response.output_text.strip()
        )

        style = data.get(
            "language_style"
        )

        if style in VALID_STYLES:
            return style

    except Exception as exc:

        print(
            "Language detection error:",
            str(exc)
        )

    return "english"


# ============================================================
# Resolve language WITH memory
# ============================================================

def resolve_language_style(
    user_id: str,
    message: str,
):
    saved_style = get_user_language(
        user_id
    )

    # --------------------------------------------------------
    # Urdu script is explicit
    # --------------------------------------------------------

    if contains_urdu_script(
        message
    ):

        style = detect_language_style(
            message
        )

        save_user_language(
            user_id,
            style,
        )

        return style

    # --------------------------------------------------------
    # Short messages inherit conversation language
    #
    # Example:
    # Ayera
    # yes
    # 4 PM
    # --------------------------------------------------------

    if (
        saved_style
        and is_short_ambiguous_message(
            message
        )
    ):
        return saved_style

    # --------------------------------------------------------
    # Detect normal message
    # --------------------------------------------------------

    style = detect_language_style(
        message
    )

    save_user_language(
        user_id,
        style,
    )

    return style


# ============================================================
# Localize reply
# ============================================================

def localize_reply(
    reply: str,
    language_style: str,
):

    if not reply:
        return reply

    if language_style == "english":
        return reply

    instructions = {
        "urdu": """
Rewrite the response in friendly, natural Urdu
using Urdu script.
""",

        "roman_urdu": """
Rewrite the response in natural Pakistani Roman Urdu.
Use Latin characters, not Urdu script.
Keep it conversational and simple.
""",

        "mixed": """
Rewrite the response in a natural mixture of
English and Roman Urdu, similar to casual
Pakistani conversation.
""",
    }

    instruction = instructions.get(
        language_style
    )

    if not instruction:
        return reply

    prompt = f"""
You are localizing a response from
Glow & Grace Salon's AI appointment assistant.

{instruction}

IMPORTANT RULES:

Do NOT change any factual information.

Preserve exactly:
- Booking IDs
- customer names
- phone numbers
- dates
- appointment times
- prices
- service names
- staff names
- URLs
- booking status

Do not invent information.

Keep these salon service names understandable:
Haircut
Hair Coloring
Facial
Manicure
Bridal Consultation

If the response contains Yes / No instructions,
translate the surrounding wording naturally,
but the customer may still reply with Yes or No.

Keep the answer concise.

Original response:

{reply}

Return ONLY the localized response.
"""

    try:

        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        localized = (
            response.output_text
            .strip()
        )

        if localized:
            return localized

    except Exception as exc:

        print(
            "Reply localization error:",
            str(exc)
        )

    return reply
