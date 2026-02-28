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


def test_venue_config_requires_browser_default_false():
    """VenueConfig with no requires_browser should default to False."""
    vc = VenueConfig(name="Test", url="https://example.com", location="123 Main St")
    assert vc.requires_browser is False
