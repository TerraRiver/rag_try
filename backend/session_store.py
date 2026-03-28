import os
import sqlite3
import json
from pathlib import Path

from debug_logger import debug_log
from env_loader import load_project_env

load_project_env()


DEFAULT_RECENT_MESSAGE_LIMIT = int(os.getenv("SESSION_RECENT_MESSAGE_LIMIT", "4"))
DEFAULT_HISTORY_MESSAGE_LIMIT = int(os.getenv("SESSION_HISTORY_MESSAGE_LIMIT", "40"))
MAX_STORED_MESSAGES = int(os.getenv("SESSION_MAX_STORED_MESSAGES", "120"))


def _debug_log(message: str) -> None:
    debug_log("session", message)


def _db_path() -> Path:
    return Path(os.getenv("SESSION_DB_PATH", "./session_state.db"))


def _connect() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_session_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
            ON messages(session_id, id)
            """
        )
        _ensure_message_sources_column(conn)


def _ensure_message_sources_column(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(messages)").fetchall()
    if any(column["name"] == "source_nodes" for column in columns):
        return

    conn.execute(
        """
        ALTER TABLE messages
        ADD COLUMN source_nodes TEXT NOT NULL DEFAULT '[]'
        """
    )


def _prune_session_messages(conn: sqlite3.Connection, session_id: str) -> None:
    if MAX_STORED_MESSAGES <= 0:
        return

    deleted = conn.execute(
        """
        DELETE FROM messages
        WHERE session_id = ?
          AND id NOT IN (
              SELECT id
              FROM messages
              WHERE session_id = ?
              ORDER BY id DESC
              LIMIT ?
          )
        """,
        (session_id, session_id, MAX_STORED_MESSAGES),
    ).rowcount

    if deleted and deleted > 0:
        _debug_log(
            f"prune messages session_id={session_id} deleted={deleted} keep_limit={MAX_STORED_MESSAGES}"
        )


def ensure_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (session_id)
            VALUES (?)
            ON CONFLICT(session_id) DO NOTHING
            """,
            (session_id,),
        )


def get_session_context(
    session_id: str,
    recent_limit: int = DEFAULT_RECENT_MESSAGE_LIMIT,
) -> tuple[str, list[dict]]:
    ensure_session(session_id)

    with _connect() as conn:
        session_row = conn.execute(
            "SELECT summary FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        message_rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, recent_limit),
        ).fetchall()

    recent_messages = [
        {"role": row["role"], "content": row["content"]}
        for row in reversed(message_rows)
    ]
    _debug_log(
        f"load context session_id={session_id} summary_len={len(session_row['summary'] if session_row else '')} recent_messages={len(recent_messages)}"
    )
    return (session_row["summary"] if session_row else "", recent_messages)


def append_messages(session_id: str, messages: list[dict]) -> None:
    if not messages:
        return

    ensure_session(session_id)
    payload = [
        (
            session_id,
            message["role"],
            message["content"],
            json.dumps(message.get("source_nodes", []), ensure_ascii=False),
        )
        for message in messages
        if message.get("role") and message.get("content")
    ]
    if not payload:
        return

    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO messages (session_id, role, content, source_nodes)
            VALUES (?, ?, ?, ?)
            """,
            payload,
        )
        conn.execute(
            """
            UPDATE sessions
            SET updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (session_id,),
        )
        _prune_session_messages(conn, session_id)
    _debug_log(f"append messages session_id={session_id} count={len(payload)}")


def update_session_summary(session_id: str, summary: str) -> None:
    ensure_session(session_id)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET summary = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            (summary, session_id),
        )
    _debug_log(f"update summary session_id={session_id} summary_len={len(summary)}")


def get_session_messages(
    session_id: str,
    limit: int = DEFAULT_HISTORY_MESSAGE_LIMIT,
) -> list[dict]:
    ensure_session(session_id)

    with _connect() as conn:
        if limit and limit > 0:
            rows = conn.execute(
                """
                SELECT id, role, content, source_nodes
                FROM (
                    SELECT id, role, content, source_nodes
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, role, content, source_nodes
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

    messages: list[dict] = []
    for row in rows:
        try:
            source_nodes = json.loads(row["source_nodes"] or "[]")
        except json.JSONDecodeError:
            source_nodes = []

        messages.append(
            {
                "id": f"message-{row['id']}",
                "role": row["role"],
                "content": row["content"],
                "source_nodes": source_nodes if isinstance(source_nodes, list) else [],
            }
        )

    _debug_log(
        f"load messages session_id={session_id} count={len(messages)} limit={limit}"
    )
    return messages
