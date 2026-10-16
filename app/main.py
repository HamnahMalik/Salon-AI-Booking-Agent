import os
import tempfile
import requests

from fastapi import (
    FastAPI,
    Request,
    UploadFile,
    File,
    Form,
)

from fastapi.responses import (
    PlainTextResponse,
    HTMLResponse,
)

from pydantic import BaseModel


# ============================================================
# Salon modules
# ============================================================

from router import detect_intent
from rag import ask_salon

from booking import (
    update_booking_session,
    get_missing_booking_fields,
    ask_for_missing_booking_field,
    prepare_booking_confirmation,
    handle_booking_confirmation,
)

from session_store import (
    get_session,
)

from cancellation import (
    start_cancellation,
    handle_cancellation,
)

from reschedule import (
    start_reschedule,
    handle_reschedule,
)

from language_service import (
    resolve_language_style,
    localize_reply,
)

from voice_service import (
    transcribe_whatsapp_voice,
    transcribe_audio_file,
    create_speech_base64,
    send_whatsapp_voice_reply,
)


# ============================================================
# FastAPI
# ============================================================

app = FastAPI(
    title="Glow & Grace Salon AI Agent"
)


# ============================================================
# Environment
# ============================================================

VERIFY_TOKEN = os.getenv(
    "WHATSAPP_VERIFY_TOKEN",
    "salon_verify_token_2026",
)

WHATSAPP_TOKEN = os.getenv(
    "WHATSAPP_TOKEN"
)

WHATSAPP_PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_NUMBER_ID"
)

WHATSAPP_API_VERSION = os.getenv(
    "WHATSAPP_API_VERSION",
    "v21.0",
)


# ============================================================
# Health
# ============================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "app": "Glow & Grace Salon AI Agent",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# WhatsApp text sender
# ============================================================

def send_whatsapp_message(
    recipient_id: str,
    message: str,
):
    if not WHATSAPP_TOKEN:
        print(
            "WHATSAPP_TOKEN missing."
        )
        return False

    if not WHATSAPP_PHONE_NUMBER_ID:
        print(
            "WHATSAPP_PHONE_NUMBER_ID missing."
        )
        return False

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
            "text",

        "text": {
            "body":
                message
        },
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        print(
            "WhatsApp send status:",
            response.status_code,
        )

        print(
            "WhatsApp response:",
            response.text,
        )

        return response.ok

    except Exception as exc:
        print(
            "WhatsApp send error:",
            str(exc),
        )

        return False


# ============================================================
# WhatsApp message extraction
# ============================================================

def extract_message(
    payload: dict
):
    try:
        entries = payload.get(
            "entry",
            []
        )

        if not entries:
            return None

        changes = (
            entries[0]
            .get(
                "changes",
                []
            )
        )

        if not changes:
            return None

        value = (
            changes[0]
            .get(
                "value",
                {}
            )
        )

        messages = value.get(
            "messages",
            []
        )

        if not messages:
            return None

        message = messages[0]

        sender_id = message.get(
            "from"
        )

        message_type = message.get(
            "type"
        )

        if message_type == "text":

            text = (
                message
                .get(
                    "text",
                    {}
                )
                .get(
                    "body",
                    ""
                )
                .strip()
            )

            return {
                "sender_id":
                    sender_id,

                "message_type":
                    "text",

                "text":
                    text,

                "media_id":
                    None,
            }

        if message_type == "audio":

            audio = message.get(
                "audio",
                {}
            )

            return {
                "sender_id":
                    sender_id,

                "message_type":
                    "audio",

                "text":
                    None,

                "media_id":
                    audio.get(
                        "id"
                    ),
            }

        return {
            "sender_id":
                sender_id,

            "message_type":
                message_type,

            "text":
                None,

            "media_id":
                None,
        }

    except Exception as exc:
        print(
            "Webhook parsing error:",
            str(exc),
        )

        return None


# ============================================================
# WhatsApp status events
# ============================================================

def process_status_event(
    payload: dict
):
    try:
        for entry in payload.get(
            "entry",
            []
        ):

            for change in entry.get(
                "changes",
                []
            ):

                value = change.get(
                    "value",
                    {}
                )

                for status in value.get(
                    "statuses",
                    []
                ):

                    print(
                        "WhatsApp status:",
                        {
                            "id":
                                status.get(
                                    "id"
                                ),

                            "status":
                                status.get(
                                    "status"
                                ),

                            "recipient":
                                status.get(
                                    "recipient_id"
                                ),
                        }
                    )

    except Exception as exc:
        print(
            "Status processing error:",
            str(exc),
        )


# ============================================================
# Booking workflow
# ============================================================

def handle_booking_flow(
    user_id: str,
    user_text: str,
):
    booking_data = (
        update_booking_session(
            user_id=user_id,
            message=user_text,
        )
    )

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

    return (
        prepare_booking_confirmation(
            user_id=user_id,
            booking_data=booking_data,
        )
    )


# ============================================================
# Internal salon logic
# ============================================================

def generate_internal_reply(
    user_id: str,
    user_text: str,
):
    user_text = (
        user_text or ""
    ).strip()

    if not user_text:
        return (
            "Please send me a message "
            "and I'll be happy to help."
        )

    # ========================================================
    # Existing workflow first
    # ========================================================

    existing_session = get_session(
        user_id
    )

    if existing_session:

        session_type = (
            existing_session.get(
                "session_type"
            )
        )

        session_data = (
            existing_session.get(
                "session_data",
                {}
            )
        )

        if session_type == "cancellation":

            return handle_cancellation(
                user_id,
                user_text,
            )

        if session_type == "reschedule":

            return handle_reschedule(
                user_id,
                user_text,
            )

        if session_type == "booking":

            stage = session_data.get(
                "stage"
            )

            if (
                stage
                == "waiting_for_confirmation"
            ):

                result = (
                    handle_booking_confirmation(
                        user_id,
                        user_text,
                    )
                )

                if isinstance(
                    result,
                    dict
                ):
                    return result.get(
                        "reply",
                        "Please try again."
                    )

                if result:
                    return result

                return (
                    "Please reply Yes to confirm "
                    "or No to cancel."
                )

            return handle_booking_flow(
                user_id,
                user_text,
            )

    # ========================================================
    # New intent
    # ========================================================

    try:
        intent = detect_intent(
            user_text
        )

        print(
            "Detected intent:",
            intent,
        )

    except Exception as exc:
        print(
            "Intent error:",
            str(exc),
        )

        intent = "unknown"

    if isinstance(
        intent,
        dict
    ):
        intent = intent.get(
            "intent",
            "unknown",
        )

    # ========================================================
    # Routing
    # ========================================================

    if intent == "book_appointment":

        return handle_booking_flow(
            user_id,
            user_text,
        )

    if intent == "cancel_appointment":

        return start_cancellation(
            user_id
        )

    if intent == "reschedule_appointment":

        return start_reschedule(
            user_id
        )

    if intent == "salon_question":

        try:
            return ask_salon(
                user_text
            )

        except Exception as exc:
            print(
                "RAG error:",
                str(exc),
            )

            return (
                "I couldn't access the salon information "
                "right now. Please try again."
            )

    if intent == "greeting":

        return (
            "Hello! Welcome to Glow & Grace Salon. "
            "I can help with services, prices, "
            "bookings, cancellations, and rescheduling. "
            "How can I help?"
        )

    # ========================================================
    # RAG fallback
    # ========================================================

    try:
        rag_reply = ask_salon(
            user_text
        )

        if rag_reply:
            return rag_reply

    except Exception as exc:
        print(
            "Fallback RAG error:",
            str(exc),
        )

    return (
        "I can help with salon services, prices, "
        "appointments, cancellations, and rescheduling. "
        "What would you like to do?"
    )


# ============================================================
# Generate multilingual response + language
# ============================================================

def generate_reply_with_style(
    user_id: str,
    user_text: str,
):
    language_style = (
        resolve_language_style(
            user_id=user_id,
            message=user_text,
        )
    )

    print(
        "Resolved language style:",
        language_style,
    )

    internal_reply = (
        generate_internal_reply(
            user_id=user_id,
            user_text=user_text,
        )
    )

    reply = localize_reply(
        reply=internal_reply,
        language_style=language_style,
    )

    return (
        reply,
        language_style,
    )


def generate_reply(
    user_id: str,
    user_text: str,
):
    reply, _ = (
        generate_reply_with_style(
            user_id=user_id,
            user_text=user_text,
        )
    )

    return reply


# ============================================================
# Webhook verification
# ============================================================

@app.get(
    "/webhook",
    response_class=PlainTextResponse,
)
async def verify_webhook(
    request: Request
):
    params = request.query_params

    mode = params.get(
        "hub.mode"
    )

    token = params.get(
        "hub.verify_token"
    )

    challenge = params.get(
        "hub.challenge"
    )

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):
        return PlainTextResponse(
            content=challenge or "",
            status_code=200,
        )

    return PlainTextResponse(
        content="Verification failed",
        status_code=403,
    )


# ============================================================
# WhatsApp webhook
# ============================================================

@app.post("/webhook")
async def whatsapp_webhook(
    request: Request
):
    payload = (
        await request.json()
    )

    print(
        "Incoming webhook:",
        payload,
    )

    process_status_event(
        payload
    )

    incoming = extract_message(
        payload
    )

    if not incoming:
        return {
            "status":
                "ignored"
        }

    sender_id = incoming.get(
        "sender_id"
    )

    message_type = incoming.get(
        "message_type"
    )

    if not sender_id:
        return {
            "status":
                "ignored"
        }

    # ========================================================
    # WhatsApp text → text reply
    # ========================================================

    if message_type == "text":

        try:
            reply = generate_reply(
                user_id=sender_id,
                user_text=incoming.get(
                    "text"
                ),
            )

        except Exception as exc:
            print(
                "Text processing error:",
                str(exc),
            )

            reply = (
                "Sorry, something went wrong. "
                "Please try again."
            )

        send_whatsapp_message(
            sender_id,
            reply,
        )

        return {
            "status":
                "processed",

            "input_type":
                "text",

            "output_type":
                "text",
        }

    # ========================================================
    # WhatsApp voice → voice reply
    # ========================================================

    if message_type == "audio":

        media_id = incoming.get(
            "media_id"
        )

        if not media_id:

            send_whatsapp_message(
                sender_id,
                (
                    "I received your voice message "
                    "but couldn't access the audio."
                ),
            )

            return {
                "status":
                    "audio_missing"
            }

        try:
            transcript = (
                transcribe_whatsapp_voice(
                    media_id
                )
            )

            print(
                "WhatsApp transcript:",
                transcript,
            )

            (
                reply,
                language_style,
            ) = generate_reply_with_style(
                user_id=sender_id,
                user_text=transcript,
            )

            # Try voice reply first
            voice_sent = (
                send_whatsapp_voice_reply(
                    recipient_id=sender_id,
                    reply_text=reply,
                    language_style=language_style,
                )
            )

            # Text fallback if audio sending fails
            if not voice_sent:

                send_whatsapp_message(
                    sender_id,
                    reply,
                )

        except Exception as exc:

            print(
                "WhatsApp voice processing error:",
                str(exc),
            )

            send_whatsapp_message(
                sender_id,
                (
                    "Sorry, I couldn't process "
                    "that voice message. "
                    "Please try again."
                ),
            )

        return {
            "status":
                "processed",

            "input_type":
                "audio",

            "output_type":
                "audio",
        }

    # ========================================================
    # Unsupported
    # ========================================================

    send_whatsapp_message(
        sender_id,
        (
            "I currently support text messages "
            "and voice notes."
        ),
    )

    return {
        "status":
            "unsupported_message"
    }


# ============================================================
# Browser text endpoint
# ============================================================

class ChatRequest(
    BaseModel
):
    user_id: str
    message: str


@app.post("/chat")
def chat(
    chat_request: ChatRequest
):
    return {
        "reply":
            generate_reply(
                user_id=chat_request.user_id,
                user_text=chat_request.message,
            )
    }


# ============================================================
# Browser voice endpoint
# ============================================================

@app.post("/chat-audio")
async def chat_audio(
    user_id: str = Form(...),
    audio: UploadFile = File(...),
):
    temp_path = None

    try:
        original_name = (
            audio.filename
            or "voice.webm"
        )

        extension = (
            os.path.splitext(
                original_name
            )[1]
        )

        if not extension:
            extension = ".webm"

        temp_file = (
            tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension,
            )
        )

        temp_path = temp_file.name

        audio_bytes = (
            await audio.read()
        )

        temp_file.write(
            audio_bytes
        )

        temp_file.close()

        # ----------------------------------------------------
        # Transcribe
        # ----------------------------------------------------

        transcript = (
            transcribe_audio_file(
                temp_path
            )
        )

        print(
            "Browser voice transcript:",
            transcript,
        )

        # ----------------------------------------------------
        # Run same salon agent
        # ----------------------------------------------------

        (
            reply,
            language_style,
        ) = generate_reply_with_style(
            user_id=user_id,
            user_text=transcript,
        )

        # ----------------------------------------------------
        # Create voice reply
        # ----------------------------------------------------

        audio_reply = (
            create_speech_base64(
                text=reply,
                language_style=language_style,
            )
        )

        return {
            "transcript":
                transcript,

            "reply":
                reply,

            "audio_reply":
                audio_reply,

            "language_style":
                language_style,
        }

    except Exception as exc:

        print(
            "Browser voice error:",
            str(exc),
        )

        return {
            "error":
                True,

            "reply":
                (
                    "Sorry, I couldn't process "
                    "that voice message."
                ),
        }

    finally:

        if (
            temp_path
            and os.path.exists(
                temp_path
            )
        ):

            try:
                os.unlink(
                    temp_path
                )

            except Exception:
                pass


# ============================================================
# Browser UI
# ============================================================

@app.get(
    "/chat-ui",
    response_class=HTMLResponse,
)
def chat_ui():

    html = """
<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Glow & Grace Salon</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f5f5f5;
    margin: 0;
    padding: 0;
}

.container {
    width: 100%;
    max-width: 650px;
    margin: 30px auto;
    background: white;
    border-radius: 12px;
    overflow: hidden;
    box-shadow:
        0 3px 15px rgba(0,0,0,0.12);
}

.header {
    padding: 20px;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    border-bottom: 1px solid #eee;
}

.subtitle {
    font-size: 13px;
    font-weight: normal;
    margin-top: 5px;
}

#chat {
    height: 500px;
    overflow-y: auto;
    padding: 20px;
}

.message {
    margin-bottom: 14px;
    white-space: pre-wrap;
    line-height: 1.4;
}

.user {
    text-align: right;
}

.user span {
    display: inline-block;
    background: #e8e8e8;
    padding: 10px 14px;
    border-radius: 14px;
    max-width: 80%;
    text-align: left;
}

.bot span {
    display: inline-block;
    background: #f3f3f3;
    padding: 10px 14px;
    border-radius: 14px;
    max-width: 80%;
}

.system {
    text-align: center;
}

.system span {
    display: inline-block;
    background: #fafafa;
    padding: 6px 10px;
    border-radius: 10px;
    font-size: 12px;
}

.audio-message {
    margin-top: 8px;
}

.audio-message audio {
    width: 100%;
    max-width: 350px;
}

.input-area {
    display: flex;
    gap: 8px;
    padding: 15px;
    border-top: 1px solid #eee;
}

#message {
    flex: 1;
    min-width: 0;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 8px;
    font-size: 16px;
}

button {
    padding: 12px 15px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 15px;
}

.recording {
    font-weight: bold;
}

#fileInput {
    display: none;
}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        Glow & Grace Salon

        <div class="subtitle">
            Multilingual Voice & Text AI Assistant
        </div>

    </div>


    <div id="chat">

        <div class="message bot">

            <span>
Hello! Welcome to Glow & Grace Salon.
You can type or send a voice message.
            </span>

        </div>

    </div>


    <div class="input-area">

        <input
            id="message"
            type="text"
            placeholder="English, Urdu or Roman Urdu..."
            autocomplete="off"
        >

        <button
            id="recordButton"
            onclick="toggleRecording()"
            title="Record voice"
        >
            🎤
        </button>

        <button
            onclick="document.getElementById('fileInput').click()"
            title="Upload audio"
        >
            📎
        </button>

        <input
            id="fileInput"
            type="file"
            accept="audio/*"
            onchange="uploadAudioFile(this)"
        >

        <button onclick="sendMessage()">
            Send
        </button>

    </div>

</div>


<script>

let userId =
    localStorage.getItem(
        "salon_user_id"
    );


if (!userId) {

    userId =
        "browser-" +
        crypto.randomUUID();

    localStorage.setItem(
        "salon_user_id",
        userId
    );

}


const messageInput =
    document.getElementById(
        "message"
    );


messageInput.addEventListener(
    "keypress",
    function(event) {

        if (
            event.key === "Enter"
        ) {

            sendMessage();

        }

    }
);


// ==========================================================
// Display text
// ==========================================================

function addMessage(
    text,
    sender
) {

    const chat =
        document.getElementById(
            "chat"
        );

    const div =
        document.createElement(
            "div"
        );

    div.className =
        "message " + sender;

    const span =
        document.createElement(
            "span"
        );

    span.textContent =
        text;

    div.appendChild(
        span
    );

    chat.appendChild(
        div
    );

    chat.scrollTop =
        chat.scrollHeight;

}


// ==========================================================
// Display bot audio
// ==========================================================

function addAudioMessage(
    audioSource
) {

    const chat =
        document.getElementById(
            "chat"
        );

    const div =
        document.createElement(
            "div"
        );

    div.className =
        "message bot audio-message";


    const audio =
        document.createElement(
            "audio"
        );

    audio.controls =
        true;

    audio.src =
        audioSource;


    div.appendChild(
        audio
    );

    chat.appendChild(
        div
    );

    chat.scrollTop =
        chat.scrollHeight;


    // Automatically play voice replies.
    // Browsers may block autoplay in some situations.

    audio.play().catch(
        function() {
            // User can press Play manually.
        }
    );

}


// ==========================================================
// Text chat
// ==========================================================

async function sendMessage() {

    const text =
        messageInput.value.trim();

    if (!text) {
        return;
    }

    addMessage(
        text,
        "user"
    );

    messageInput.value =
        "";

    try {

        const response =
            await fetch(
                "/chat",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                user_id:
                                    userId,

                                message:
                                    text
                            }
                        )
                }
            );

        const data =
            await response.json();

        addMessage(
            data.reply ||
            "No response received.",
            "bot"
        );

    }

    catch (error) {

        addMessage(
            "Something went wrong. Please try again.",
            "bot"
        );

    }

}


// ==========================================================
// Voice recorder
// ==========================================================

let mediaRecorder = null;
let audioChunks = [];
let audioStream = null;
let isRecording = false;


async function toggleRecording() {

    if (!isRecording) {

        await startRecording();

    }

    else {

        stopRecording();

    }

}


async function startRecording() {

    try {

        audioStream =
            await navigator
            .mediaDevices
            .getUserMedia(
                {
                    audio: true
                }
            );


        audioChunks = [];


        mediaRecorder =
            new MediaRecorder(
                audioStream
            );


        mediaRecorder.ondataavailable =
            function(event) {

                if (
                    event.data.size > 0
                ) {

                    audioChunks.push(
                        event.data
                    );

                }

            };


        mediaRecorder.onstop =
            async function() {

                const mimeType =
                    mediaRecorder.mimeType
                    ||
                    "audio/webm";


                const blob =
                    new Blob(
                        audioChunks,
                        {
                            type:
                                mimeType
                        }
                    );


                if (audioStream) {

                    audioStream
                    .getTracks()
                    .forEach(
                        track =>
                            track.stop()
                    );

                }


                await sendAudioBlob(
                    blob,
                    "browser-voice.webm"
                );

            };


        mediaRecorder.start();

        isRecording =
            true;


        const button =
            document.getElementById(
                "recordButton"
            );


        button.textContent =
            "⏹";

        button.classList.add(
            "recording"
        );


        addMessage(
            "Recording...",
            "system"
        );

    }

    catch (error) {

        console.error(
            error
        );


        addMessage(
            "Microphone access was not available.",
            "bot"
        );

    }

}


function stopRecording() {

    if (
        mediaRecorder
        &&
        mediaRecorder.state
        !== "inactive"
    ) {

        mediaRecorder.stop();

    }


    isRecording =
        false;


    const button =
        document.getElementById(
            "recordButton"
        );


    button.textContent =
        "🎤";

    button.classList.remove(
        "recording"
    );

}


// ==========================================================
// Process voice response
// ==========================================================

function handleVoiceResponse(
    data
) {

    if (
        data.transcript
    ) {

        addMessage(
            "You said: " +
            data.transcript,
            "system"
        );

    }


    if (
        data.reply
    ) {

        addMessage(
            data.reply,
            "bot"
        );

    }


    if (
        data.audio_reply
    ) {

        addAudioMessage(
            data.audio_reply
        );

    }

}


// ==========================================================
// Recorded voice
// ==========================================================

async function sendAudioBlob(
    blob,
    filename
) {

    addMessage(
        "🎤 Voice message",
        "user"
    );


    addMessage(
        "Processing voice...",
        "system"
    );


    const formData =
        new FormData();


    formData.append(
        "user_id",
        userId
    );


    formData.append(
        "audio",
        blob,
        filename
    );


    try {

        const response =
            await fetch(
                "/chat-audio",
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );


        const data =
            await response.json();


        handleVoiceResponse(
            data
        );

    }

    catch (error) {

        console.error(
            error
        );


        addMessage(
            "Voice message could not be processed.",
            "bot"
        );

    }

}


// ==========================================================
// Uploaded audio
// ==========================================================

async function uploadAudioFile(
    input
) {

    const file =
        input.files[0];


    if (!file) {
        return;
    }


    addMessage(
        "🎤 Voice message",
        "user"
    );


    addMessage(
        "Processing voice...",
        "system"
    );


    const formData =
        new FormData();


    formData.append(
        "user_id",
        userId
    );


    formData.append(
        "audio",
        file,
        file.name
    );


    try {

        const response =
            await fetch(
                "/chat-audio",
                {
                    method:
                        "POST",

                    body:
                        formData
                }
            );


        const data =
            await response.json();


        handleVoiceResponse(
            data
        );

    }

    catch (error) {

        console.error(
            error
        );


        addMessage(
            "Audio file could not be processed.",
            "bot"
        );

    }


    input.value =
        "";

}

</script>

</body>

</html>
"""

    return HTMLResponse(
        content=html
    )
