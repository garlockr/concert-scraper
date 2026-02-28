from __future__ import annotations

import datetime

from concert_scraper.models import Event, VenueConfig


def test_event_creation_with_all_fields():
    """Create an Event with all fields populated, assert all values are set correctly."""
    event = Event(
        title="The Black Keys",
        date=datetime.date(2025, 6, 15),
        doors_time=datetime.time(18, 0),
        show_time=datetime.time(19, 30),
        end_time=datetime.time(22, 0),
        artists=["The Black Keys", "Opening Act"],
        price="$45",
        ticket_url="https://example.com/tickets",
        description="Summer tour stop",
        venue_name="The Fillmore",
        venue_location="1805 Geary Blvd, San Francisco, CA",
    )
    assert event.title == "The Black Keys"
    assert event.date == datetime.date(2025, 6, 15)
    assert event.doors_time == datetime.time(18, 0)
    assert event.show_time == datetime.time(19, 30)
    assert event.end_time == datetime.time(22, 0)
    assert event.artists == ["The Black Keys", "Opening Act"]
    assert event.price == "$45"
    assert event.ticket_url == "https://example.com/tickets"
    assert event.description == "Summer tour stop"
    assert event.venue_name == "The Fillmore"
    assert event.venue_location == "1805 Geary Blvd, San Francisco, CA"


def test_event_creation_minimal():
    """Create an Event with only required fields; check defaults."""
    event = Event(
        title="Some Show",
        date=datetime.date(2025, 7, 1),
        venue_name="Test Venue",
    )
    assert event.doors_time is None
    assert event.show_time is None
    assert event.end_time is None
    assert event.artists == []
    assert event.price is None
    assert event.ticket_url is None
    assert event.description is None
    assert event.venue_location is None


def test_normalized_key_case_insensitive():
    """Same title in different cases should produce the same key."""
    e1 = Event(title="The Black Keys", date=datetime.date(2025, 6, 15), venue_name="Venue")
    e2 = Event(title="the black keys", date=datetime.date(2025, 6, 15), venue_name="Venue")
    assert e1.normalized_key() == e2.normalized_key()


def test_normalized_key_strips_the():
    """'The National' and 'National' should produce the same key."""
    e1 = Event(title="The National", date=datetime.date(2025, 6, 15), venue_name="Venue")
    e2 = Event(title="National", date=datetime.date(2025, 6, 15), venue_name="Venue")
    assert e1.normalized_key() == e2.normalized_key()


def test_normalized_key_strips_punctuation():
    """Punctuation differences should not affect the key."""
    e1 = Event(
        title="King Gizzard & The Lizard Wizard",
        date=datetime.date(2025, 6, 15),
        venue_name="Venue",
    )
    e2 = Event(
        title="King Gizzard the Lizard Wizard",
        date=datetime.date(2025, 6, 15),
        venue_name="Venue",
    )
    assert e1.normalized_key() == e2.normalized_key()


def test_normalized_key_different_dates():
    """Same title at same venue on different dates should produce different keys."""
    e1 = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="Venue")
    e2 = Event(title="Show", date=datetime.date(2025, 6, 16), venue_name="Venue")
    assert e1.normalized_key() != e2.normalized_key()


def test_start_datetime_defaults_to_8pm():
    """Event with no times should have start_datetime at 20:00."""
    event = Event(title="Show", date=datetime.date(2025, 7, 1), venue_name="Venue")
    assert event.start_datetime == datetime.datetime(2025, 7, 1, 20, 0)


def test_start_datetime_uses_show_time():
    """Event with show_time should use it for start_datetime."""
    event = Event(
        title="Show",
        date=datetime.date(2025, 7, 1),
        venue_name="Venue",
        show_time=datetime.time(19, 30),
    )
    assert event.start_datetime == datetime.datetime(2025, 7, 1, 19, 30)


def test_start_datetime_falls_back_to_doors_time():
    """Event with doors_time but no show_time should use doors_time."""
    event = Event(
        title="Show",
        date=datetime.date(2025, 7, 1),
        venue_name="Venue",
        doors_time=datetime.time(18, 0),
    )
    assert event.start_datetime == datetime.datetime(2025, 7, 1, 18, 0)


def test_end_date_defaults_to_none():
    """end_date should default to None for backward compatibility."""
    event = Event(title="Show", date=datetime.date(2025, 7, 1), venue_name="Venue")
    assert event.end_date is None


def test_end_datetime_uses_end_date():
    """end_datetime should use end_date when set for multi-day events."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        show_time=datetime.time(19, 0),
        end_time=datetime.time(23, 0),
        venue_name="Venue",
    )
    assert event.end_datetime == datetime.datetime(2025, 6, 15, 23, 0)


def test_end_datetime_without_end_date():
    """end_datetime should use date when end_date is not set (single-day)."""
    event = Event(
        title="Show",
        date=datetime.date(2025, 6, 15),
        show_time=datetime.time(19, 0),
        end_time=datetime.time(23, 0),
        venue_name="Venue",
    )
    assert event.end_datetime == datetime.datetime(2025, 6, 15, 23, 0)


def test_end_datetime_multiday_default_duration():
    """Without end_time, multi-day end_datetime should be on end_date + default duration."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        show_time=datetime.time(19, 0),
        venue_name="Venue",
    )
    assert event.end_datetime == datetime.datetime(2025, 6, 15, 22, 0)


def test_end_datetime_multiday_midnight_crossing():
    """Multi-day event with end_time before start should roll to next day."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        show_time=datetime.time(21, 0),
        end_time=datetime.time(1, 0),
        venue_name="Venue",
    )
    assert event.end_datetime == datetime.datetime(2025, 6, 16, 1, 0)


def test_normalized_key_with_date_range():
    """Multi-day event key should use start..end date format."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        venue_name="Venue",
    )
    key = event.normalized_key()
    assert "2025-06-13..2025-06-15" in key


def test_normalized_key_single_day_no_range():
    """Single-day event key should just use the date, not a range."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="Venue")
    key = event.normalized_key()
    assert "2025-06-15" in key
    assert ".." not in key


def test_covered_day_keys():
    """covered_day_keys should return one key per day in the range."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        venue_name="Venue",
    )
    keys = event.covered_day_keys()
    assert len(keys) == 3
    assert "Venue|2025-06-13|fest" in keys
    assert "Venue|2025-06-14|fest" in keys
    assert "Venue|2025-06-15|fest" in keys


def test_covered_day_keys_single_day():
    """Single-day event should return one key matching normalized_key()."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="Venue")
    keys = event.covered_day_keys()
    assert len(keys) == 1
    assert keys[0] == event.normalized_key()


def test_json_roundtrip_with_end_date():
    """Event with end_date should survive JSON serialization/deserialization."""
    event = Event(
        title="Fest",
        date=datetime.date(2025, 6, 13),
        end_date=datetime.date(2025, 6, 15),
        venue_name="Venue",
    )
    json_str = event.model_dump_json()
    restored = Event.model_validate_json(json_str)
    assert restored.end_date == datetime.date(2025, 6, 15)
    assert restored.date == datetime.date(2025, 6, 13)


def test_json_roundtrip_without_end_date():
    """Event without end_date should survive JSON roundtrip with None."""
    event = Event(title="Show", date=datetime.date(2025, 7, 1), venue_name="Venue")
    json_str = event.model_dump_json()
    restored = Event.model_validate_json(json_str)
    assert restored.end_date is None


def test_venue_config_requires_browser_default_false():
    """VenueConfig with no requires_browser should default to False."""
    vc = VenueConfig(name="Test", url="https://example.com", location="123 Main St")
    assert vc.requires_browser is False
