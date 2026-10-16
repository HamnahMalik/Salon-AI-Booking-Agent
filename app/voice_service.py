import os
import json
import base64
import tempfile
import requests

from openai import OpenAI


client = OpenAI()


WHATSAPP_TOKEN = os.getenv(
    "WHATSAPP_TOKEN"
)

WHATSAPP_API_VERSION = os.getenv(
    "WHATSAPP_API_VERSION",
    "v21.0",
)

WHATSAPP_PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_NUMBER_ID"
)


# ============================================================
# WhatsApp media URL
# ============================================================

def get_whatsapp_media_url(
    media_id: str
):
    if not WHATSAPP_TOKEN:
        raise RuntimeError(
            "WHATSAPP_TOKEN is missing."
        )

    url = (
        f"https://graph.facebook.com/"
        f"{WHATSAPP_API_VERSION}/"
        f"{media_id}"
    )

    headers = {
        "Authorization":
            f"Bearer {WHATSAPP_TOKEN}"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    media_url = data.get(
        "url"
    )

    if not media_url:
        raise RuntimeError(
            "Meta did not return a media URL."
        )

    return media_url


# ============================================================
# Download WhatsApp audio
# ============================================================

def download_whatsapp_audio(
    media_id: str
):
    media_url = (
        get_whatsapp_media_url(
            media_id
        )
    )

    headers = {
        "Authorization":
            f"Bearer {WHATSAPP_TOKEN}"
    }

    response = requests.get(
        media_url,
        headers=headers,
        timeout=60,
    )

    response.raise_for_status()

    content_type = (
        response.headers
        .get(
            "Content-Type",
            ""
        )
        .lower()
    )

    suffix = ".ogg"

    if "mpeg" in content_type:
        suffix = ".mp3"

    elif "mp4" in content_type:
        suffix = ".mp4"

    elif "wav" in content_type:
        suffix = ".wav"

    elif "webm" in content_type:
        suffix = ".webm"

    temp_file = (
        tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        )
    )

    try:
        temp_file.write(
            response.content
        )

        temp_file.close()

        return temp_file.name

    except Exception:
        temp_file.close()

        if os.path.exists(
            temp_file.name
        ):
            os.unlink(
                temp_file.name
            )

        raise


# ============================================================
# Speech to text
# ============================================================

def transcribe_audio_file(
    file_path: str
):
    with open(
        file_path,
        "rb",
    ) as audio_file:

        transcription = (
            client.audio
            .transcriptions
            .create(
                model="gpt-4o-mini-transcribe",
                file=audio_file,
                prompt=(
                    "This is a salon appointment conversation. "
                    "The speaker may use English, Urdu, "
                    "Roman Urdu, or mixed English and Urdu. "
                    "Preserve names, dates, appointment times, "
                    "booking IDs, and salon service names accurately."
                ),
            )
        )

    text = getattr(
        transcription,
        "text",
        None,
    )

    if not text:
        raise RuntimeError(
            "No transcription text returned."
        )

    return text.strip()


# ============================================================
# WhatsApp voice transcription
# ============================================================

def transcribe_whatsapp_voice(
    media_id: str
):
    file_path = None

    try:
        file_path = (
            download_whatsapp_audio(
                media_id
            )
        )

        return (
            transcribe_audio_file(
                file_path
            )
        )

    finally:
        if (
            file_path
            and os.path.exists(
                file_path
            )
        ):
            try:
                os.unlink(
                    file_path
                )

            except Exception:
                pass


# ============================================================
# Prepare reply for natural speech
#
# Roman Urdu is converted to speech-friendly Urdu script.
# The visible text response remains unchanged.
# ============================================================

def prepare_speech_text(
    reply: str,
    language_style: str,
):
    if not reply:
        return reply

    # English can go straight to TTS.
    if language_style == "english":
        return reply

    if language_style == "urdu":
        return reply

    prompt = f"""
You are preparing text for text-to-speech.

The user is interacting with a Pakistani salon assistant.

Convert the following response into natural,
speech-friendly Urdu.

The text may currently be Roman Urdu or mixed
English and Roman Urdu.

IMPORTANT:

Preserve factual information exactly:
- customer names
- booking IDs
- dates
- times
- prices
- phone numbers
- service names
- staff names

Service names such as Haircut, Hair Coloring,
Facial, Manicure and Bridal Consultation may remain
in English if that sounds natural.

Do not add new information.

Do not explain anything.

Return ONLY the text that should be spoken.

Response:

{reply}
"""

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            input=prompt,
        )

        speech_text = (
            response.output_text
            .strip()
        )

        return speech_text or reply

    except Exception as exc:
        print(
            "Speech text preparation error:",
            str(exc),
        )

        return reply


# ============================================================
# Text to speech
# ============================================================

def create_speech_file(
    text: str,
    language_style: str = "english",
):
    speech_text = (
        prepare_speech_text(
            reply=text,
            language_style=language_style,
        )
    )

    temp_file = (
        tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3",
        )
    )

    output_path = (
        temp_file.name
    )

    temp_file.close()

    try:
        with (
            client.audio.speech
            .with_streaming_response
            .create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=speech_text,
                instructions=(
                    "Speak as a warm, professional salon receptionist. "
                    "Use a natural conversational pace. "
                    "Pronounce Urdu and English words naturally. "
                    "Do not sound overly dramatic."
                ),
                response_format="mp3",
            )
        ) as response:

            response.stream_to_file(
                output_path
            )

        return output_path

    except Exception:
        if os.path.exists(
            output_path
        ):
            os.unlink(
                output_path
            )

        raise


# ============================================================
# Browser-ready Base64 audio
# ============================================================

def create_speech_base64(
    text: str,
    language_style: str = "english",
):
    file_path = None

    try:
        file_path = (
            create_speech_file(
                text=text,
                language_style=language_style,
            )
        )

        with open(
            file_path,
            "rb",
        ) as audio_file:

            encoded = (
                base64.b64encode(
                    audio_file.read()
                )
                .decode(
                    "utf-8"
                )
            )

        return (
            "data:audio/mpeg;base64,"
            + encoded
        )

    finally:
        if (
            file_path
            and os.path.exists(
                file_path
            )
        ):
            try:
                os.unlink(
                    file_path
                )

            except Exception:
                pass


# ============================================================
# Upload generated audio to WhatsApp
# ============================================================

def upload_audio_to_whatsapp(
    file_path: str
):
    if not WHATSAPP_TOKEN:
        raise RuntimeError(
            "WHATSAPP_TOKEN is missing."
        )

    if not WHATSAPP_PHONE_NUMBER_ID:
        raise RuntimeError(
            "WHATSAPP_PHONE_NUMBER_ID is missing."
        )

    url = (
        f"https://graph.facebook.com/"
        f"{WHATSAPP_API_VERSION}/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/media"
    )

    headers = {
        "Authorization":
            f"Bearer {WHATSAPP_TOKEN}"
    }

    with open(
        file_path,
        "rb",
    ) as audio_file:

        files = {
            "file": (
                "reply.mp3",
                audio_file,
                "audio/mpeg",
            )
        }

        data = {
            "messaging_product":
                "whatsapp"
        }

        response = requests.post(
            url,
            headers=headers,
            files=files,
            data=data,
            timeout=60,
        )

    response.raise_for_status()

    result = response.json()

    media_id = result.get(
        "id"
    )

    if not media_id:
        raise RuntimeError(
            "Meta did not return uploaded media ID."
        )

    return media_id


# ============================================================
# Send WhatsApp audio response
# ============================================================

def send_whatsapp_voice_reply(
    recipient_id: str,
    reply_text: str,
    language_style: str,
):
    file_path = None

    try:
        file_path = (
            create_speech_file(
                text=reply_text,
                language_style=language_style,
            )
        )

        media_id = (
            upload_audio_to_whatsapp(
                file_path
            )
        )

        url = (
            f"https://graph.facebook.com/"
            f"{WHATSAPP_API_VERSION}/"
            f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

        headers = {
            "Authorization":
                f"Bearer {WHATSAPP_TOKEN}",

            "Content-Type":
                "application/json",
        }

        payload = {
            "messaging_product":
                "whatsapp",

            "recipient_type":
                "individual",

            "to":
                recipient_id,

            "type":
                "audio",

            "audio": {
                "id":
                    media_id
            },
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(
            "WhatsApp audio status:",
            response.status_code,
        )

        print(
            "WhatsApp audio response:",
            response.text,
        )

        return response.ok

    finally:
        if (
            file_path
            and os.path.exists(
                file_path
            )
        ):
            try:
                os.unlink(
                    file_path
                )

            except Exception:
                pass
