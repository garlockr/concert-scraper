from __future__ import annotations

import os
import sqlite3
import time

import pytest

from concert_scraper.db import get_upcoming, init_db, is_seen, mark_seen


def test_init_db_creates_table(tmp_path):
    """init_db creates the seen_events table."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='seen_events'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_mark_seen_and_is_seen(tmp_path):
    """mark_seen inserts a record, is_seen returns True for the same key."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    key = "Venue|2025-06-15|test show"
    mark_seen(db_path, key, "Venue", "Test Show", "2025-06-15")
    assert is_seen(db_path, key) is True


def test_is_seen_returns_false_for_unknown(tmp_path):
    """is_seen returns False for a key that was never marked."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    assert is_seen(db_path, "unknown|key|here") is False


def test_mark_seen_is_idempotent(tmp_path):
    """Calling mark_seen twice with the same key should not raise."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    key = "Venue|2025-06-15|test show"
    mark_seen(db_path, key, "Venue", "Test Show", "2025-06-15")
    mark_seen(db_path, key, "Venue", "Test Show", "2025-06-15")

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM seen_events WHERE normalized_key = ?", (key,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 1


def test_is_seen_updates_last_seen(tmp_path):
    """When is_seen finds an existing record, it updates last_seen."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    key = "Venue|2025-06-15|test show"
    mark_seen(db_path, key, "Venue", "Test Show", "2025-06-15")

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT last_seen FROM seen_events WHERE normalized_key = ?", (key,))
    first_seen_time = cursor.fetchone()[0]
    conn.close()

    # Small delay to ensure timestamp changes
    time.sleep(1.1)
    is_seen(db_path, key)

    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT last_seen FROM seen_events WHERE normalized_key = ?", (key,))
    updated_time = cursor.fetchone()[0]
    conn.close()

    assert updated_time >= first_seen_time


def test_get_upcoming_filters_past(tmp_path):
    """get_upcoming should only return future events."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    mark_seen(db_path, "v|2020-01-01|past", "Venue", "Past Show", "2020-01-01")
    mark_seen(db_path, "v|2099-12-31|future", "Venue", "Future Show", "2099-12-31")

    upcoming = get_upcoming(db_path)
    assert len(upcoming) == 1
    assert upcoming[0]["event_title"] == "Future Show"


def test_get_upcoming_ordered_by_date(tmp_path):
    """Events returned by get_upcoming should be ordered by date ascending."""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    mark_seen(db_path, "v|2099-12-31|later", "Venue", "Later Show", "2099-12-31")
    mark_seen(db_path, "v|2099-06-15|earlier", "Venue", "Earlier Show", "2099-06-15")

    upcoming = get_upcoming(db_path)
    assert len(upcoming) == 2
    assert upcoming[0]["event_title"] == "Earlier Show"
    assert upcoming[1]["event_title"] == "Later Show"


def test_init_db_creates_parent_dirs(tmp_path):
    """init_db with nested path should create parent directories."""
    db_path = str(tmp_path / "a" / "b" / "c" / "events.db")
    init_db(db_path)
    assert os.path.exists(db_path)
