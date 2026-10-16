import sqlite3
from datetime import datetime

from session_store import DB_PATH


# ============================================================
# Initialize table
# ============================================================

def init_language_table():
    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS language_preferences (
            user_id TEXT PRIMARY KEY,
            language_style TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# Get saved language
# ============================================================

def get_user_language(
    user_id: str
):
    init_language_table()

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT language_style
        FROM language_preferences
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    row = cursor.fetchone()

    conn.close()

    if not row:
        return None

    return row[0]


# ============================================================
# Save language
# ============================================================

def save_user_language(
    user_id: str,
    language_style: str,
):
    init_language_table()

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO language_preferences (
            user_id,
            language_style,
            updated_at
        )
        VALUES (?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            language_style = excluded.language_style,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            language_style,
            datetime.utcnow().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


# ============================================================
# Clear for testing
# ============================================================

def delete_user_language(
    user_id: str
):
    init_language_table()

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM language_preferences
        WHERE user_id = ?
        """,
        (
            user_id,
        ),
    )

    conn.commit()
    conn.close()


def clear_all_languages():
    init_language_table()

    conn = sqlite3.connect(
        DB_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM language_preferences
        """
    )

    conn.commit()
    conn.close()
