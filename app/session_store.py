import json
import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH = Path("/app/data/salon.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            user_id TEXT PRIMARY KEY,
            session_type TEXT NOT NULL,
            session_data TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def get_session(user_id: str):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT user_id, session_type, session_data, updated_at
        FROM sessions
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return {
        "user_id": row["user_id"],
        "session_type": row["session_type"],
        "session_data": json.loads(row["session_data"]),
        "updated_at": row["updated_at"]
    }


def save_session(
    user_id: str,
    session_type: str,
    session_data: dict
):
    conn = get_connection()

    now = datetime.utcnow().isoformat()

    conn.execute(
        """
        INSERT INTO sessions (
            user_id,
            session_type,
            session_data,
            updated_at
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            session_type = excluded.session_type,
            session_data = excluded.session_data,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            session_type,
            json.dumps(session_data),
            now
        )
    )

    conn.commit()
    conn.close()


def delete_session(user_id: str):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM sessions
        WHERE user_id = ?
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()


def clear_all_sessions():
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM sessions
        """
    )

    conn.commit()
    conn.close()


def list_sessions():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT user_id, session_type, session_data, updated_at
        FROM sessions
        ORDER BY updated_at DESC
        """
    ).fetchall()

    conn.close()

    sessions = []

    for row in rows:
        sessions.append(
            {
                "user_id": row["user_id"],
                "session_type": row["session_type"],
                "session_data": json.loads(
                    row["session_data"]
                ),
                "updated_at": row["updated_at"]
            }
        )

    return sessions


init_db()
