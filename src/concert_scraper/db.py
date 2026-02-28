from __future__ import annotations

import os
import sqlite3


def init_db(db_path: str) -> None:
    """Initialize the SQLite database and create the seen_events table."""
    parent = os.path.dirname(db_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_key TEXT UNIQUE NOT NULL,
                venue_name TEXT NOT NULL,
                event_title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                calendar_event_id TEXT,
                first_seen TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
    finally:
        conn.close()


def is_seen(db_path: str, normalized_key: str) -> bool:
    """Check if an event has already been seen. Updates last_seen if found."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT 1 FROM seen_events WHERE normalized_key = ?",
            (normalized_key,),
        )
        found = cursor.fetchone() is not None
        if found:
            conn.execute(
                "UPDATE seen_events SET last_seen = datetime('now') WHERE normalized_key = ?",
                (normalized_key,),
            )
            conn.commit()
        return found
    finally:
        conn.close()


def mark_seen(
    db_path: str,
    normalized_key: str,
    venue_name: str,
    event_title: str,
    event_date: str,
    calendar_event_id: str = "",
) -> None:
    """Mark an event as seen in the database. Idempotent (INSERT OR IGNORE)."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT OR IGNORE INTO seen_events
               (normalized_key, venue_name, event_title, event_date, calendar_event_id)
               VALUES (?, ?, ?, ?, ?)""",
            (normalized_key, venue_name, event_title, event_date, calendar_event_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_upcoming(db_path: str) -> list[dict]:
    """Return all events with dates today or later, ordered by date ascending."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            """SELECT normalized_key, venue_name, event_title, event_date,
                      calendar_event_id, first_seen, last_seen
               FROM seen_events
               WHERE event_date >= date('now')
               ORDER BY event_date ASC"""
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
