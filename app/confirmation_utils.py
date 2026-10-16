import re


def normalize_confirmation_reply(
    text: str
):
    """
    Returns:
        "yes"
        "no"
        "unknown"

    Supports:
    English
    Roman Urdu
    Urdu script
    Natural/voice-style confirmation phrases
    """

    text = (
        text or ""
    ).strip().lower()

    if not text:
        return "unknown"

    # Remove punctuation while preserving Urdu characters.
    text = re.sub(
        r"[^\w\s\u0600-\u06FF]",
        "",
        text,
    )

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


    # ========================================================
    # Exact YES phrases
    # ========================================================

    positive_phrases = {
        # English
        "yes",
        "y",
        "yeah",
        "yep",
        "sure",
        "ok",
        "okay",
        "confirm",
        "confirmed",
        "proceed",
        "go ahead",
        "please proceed",

        # Roman Urdu
        "han",
        "haan",
        "han ji",
        "haan ji",
        "han g",
        "haan g",
        "ji",
        "jee",
        "g",
        "jee han",
        "jee haan",
        "ji han",
        "ji haan",
        "bilkul",
        "theek",
        "theek hai",
        "thik hai",
        "sahi hai",
        "kar dein",
        "kar den",
        "kr dein",
        "kr den",
        "kar do",
        "kr do",
        "confirm kar dein",
        "confirm kr dein",
        "book kar dein",
        "book kr dein",
        "booking kar dein",
        "booking kr dein",
        "cancel kar dein",
        "cancel kr dein",
        "reschedule kar dein",
        "reschedule kr dein",
        "change kar dein",
        "change kr dein",

        # Urdu script
        "ہاں",
        "ہاں جی",
        "جی",
        "جی ہاں",
        "جی بالکل",
        "بالکل",
        "ٹھیک",
        "ٹھیک ہے",
        "صحیح ہے",
        "کر دیں",
        "کر دو",
        "کنفرم",
        "کنفرم کر دیں",
        "بک کر دیں",
        "بکنگ کر دیں",
        "کینسل کر دیں",
        "ری شیڈول کر دیں",
        "تبدیل کر دیں",
    }


    # ========================================================
    # Exact NO phrases
    # ========================================================

    negative_phrases = {
        # English
        "no",
        "n",
        "nope",
        "dont",
        "do not",
        "stop",
        "never mind",
        "nevermind",
        "leave it",

        # Roman Urdu
        "na",
        "nahi",
        "nahin",
        "nai",
        "nhi",
        "nahi ji",
        "nahin ji",
        "rehne dein",
        "rehny dein",
        "rehne den",
        "rehny den",
        "mat karein",
        "mat karen",
        "mat karo",
        "na karein",
        "na karen",

        # Urdu
        "نہیں",
        "نہی",
        "نہ",
        "نہیں جی",
        "رہنے دیں",
        "مت کریں",
        "مت کرو",
        "نہ کریں",
    }


    if text in positive_phrases:
        return "yes"

    if text in negative_phrases:
        return "no"


    # ========================================================
    # Negative phrases first
    #
    # Important:
    # "cancel mat karein"
    # must be NO, not YES just because "cancel" is present.
    # ========================================================

    negative_contains = [
        "dont",
        "do not",
        "never mind",
        "leave it",

        "nahi",
        "nahin",
        "nhi",
        "rehne dein",
        "rehny dein",
        "mat kar",
        "na kar",

        "نہیں",
        "رہنے دیں",
        "مت کر",
        "نہ کر",
    ]

    for phrase in negative_contains:
        if phrase in text:
            return "no"


    # ========================================================
    # Natural affirmative phrases
    # ========================================================

    positive_contains = [
        # Generic
        "yes",
        "sure",
        "go ahead",
        "please proceed",

        # Roman Urdu
        "haan",
        "han ji",
        "haan ji",
        "jee haan",
        "ji haan",
        "bilkul",
        "theek hai",
        "sahi hai",
        "kar dein",
        "kr dein",
        "kar do",
        "kr do",

        # Urdu
        "ہاں",
        "جی ہاں",
        "بالکل",
        "ٹھیک ہے",
        "صحیح ہے",
        "کر دیں",
        "کر دو",
    ]

    for phrase in positive_contains:
        if phrase in text:
            return "yes"


    return "unknown"
