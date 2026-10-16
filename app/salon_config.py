from datetime import time


# ============================================================
# Salon configuration
# ============================================================

SALON_TIMEZONE = "Asia/Karachi"

OPENING_TIME = time(10, 0)
CLOSING_TIME = time(20, 0)

# Potential appointment start times are generated every 30 mins.
SLOT_INTERVAL_MINUTES = 30


# ============================================================
# Services
# ============================================================

SERVICE_CONFIG = {
    "Haircut": {
        "duration": 45,
        "staff": ["Sara"],
    },

    "Hair Coloring": {
        "duration": 90,
        "staff": ["Sara"],
    },

    "Facial": {
        "duration": 60,
        "staff": ["Ayesha", "Hina"],
    },

    "Manicure": {
        "duration": 45,
        "staff": ["Hina"],
    },

    "Bridal Consultation": {
        "duration": 60,
        "staff": ["Ayesha"],
    },
}


# ============================================================
# Natural-language time windows
# ============================================================

TIME_WINDOWS = {
    "morning": (
        time(10, 0),
        time(12, 0),
    ),

    "afternoon": (
        time(12, 0),
        time(17, 0),
    ),

    "evening": (
        time(17, 0),
        time(20, 0),
    ),
}
