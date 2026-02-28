from __future__ import annotations

import datetime

from concert_scraper.calendar import (
    _escape_applescript,
    build_description,
    build_location,
    build_vevent,
)
from concert_scraper.models import Event


# ---------------------------------------------------------------------------
# _escape_applescript — injection prevention
# ---------------------------------------------------------------------------


def test_escape_applescript_plain_text():
    """Plain text should pass through unchanged."""
    assert _escape_applescript("Jazz Night") == "Jazz Night"


def test_escape_applescript_escapes_double_quotes():
    """Double quotes must be escaped to prevent breaking out of string context."""
    assert _escape_applescript('He said "hello"') == 'He said \\"hello\\"'


def test_escape_applescript_escapes_backslashes():
    """Backslashes must be escaped before quotes to prevent escape sequence attacks."""
    assert _escape_applescript("path\\to\\file") == "path\\\\to\\\\file"


def test_escape_applescript_strips_newlines():
    """Newlines could break AppleScript string context and must be replaced."""
    result = _escape_applescript("line1\nline2\rline3\r\nline4")
    assert "\n" not in result
    assert "\r" not in result


def test_escape_applescript_strips_null_bytes():
    """Null bytes must be stripped to prevent truncation attacks."""
    result = _escape_applescript("before\x00after")
    assert "\x00" not in result
    assert "beforeafter" == result


def test_escape_applescript_strips_tabs():
    """Tabs should be replaced with spaces."""
    result = _escape_applescript("col1\tcol2")
    assert "\t" not in result


def test_escape_applescript_backslash_before_quote():
    """Backslash immediately before a quote must not create an unescaped quote.
    Input: \\\" should become \\\\\\" (escaped backslash + escaped quote)."""
    result = _escape_applescript('test\\"end')
    # The backslash is escaped first (\\\\), then the quote is escaped (\\")
    assert result == 'test\\\\\\"end'


def test_escape_applescript_combined_attack_string():
    """A string combining multiple injection vectors should be fully sanitized."""
    attack = 'title"\n-- evil code\r\x00'
    result = _escape_applescript(attack)
    assert '"' not in result or result.count('\\"') == result.count('"')
    assert "\n" not in result
    assert "\r" not in result
    assert "\x00" not in result


# ---------------------------------------------------------------------------
# build_location / build_description — public helpers
# ---------------------------------------------------------------------------


def test_build_location_with_address():
    """Location should combine venue name and address."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15),
                  venue_name="The Fillmore", venue_location="1805 Geary Blvd")
    assert build_location(event) == "The Fillmore — 1805 Geary Blvd"


def test_build_location_without_address():
    """Location should fall back to just the venue name."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15),
                  venue_name="The Fillmore")
    assert build_location(event) == "The Fillmore"


def test_build_description_with_all_fields():
    """Description should include doors, price, artists, description, and tickets."""
    event = Event(
        title="Show", date=datetime.date(2025, 6, 15), venue_name="Venue",
        doors_time=datetime.time(18, 0), price="$25",
        artists=["Band A", "Band B"], description="A great show",
        ticket_url="https://example.com/tickets",
    )
    desc = build_description(event)
    assert "Doors: 06:00 PM" in desc
    assert "Price: $25" in desc
    assert "Artists: Band A, Band B" in desc
    assert "A great show" in desc
    assert "Tickets: https://example.com/tickets" in desc


def test_build_description_empty():
    """Event with no optional fields should produce an empty description."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="Venue")
    assert build_description(event) == ""


# ---------------------------------------------------------------------------
# build_vevent — shared iCalendar VEVENT builder
# ---------------------------------------------------------------------------


def test_build_vevent_has_required_fields():
    """VEVENT should contain summary, dtstart, dtend, location, and uid."""
    event = Event(
        title="Jazz Night", date=datetime.date(2025, 6, 15),
        venue_name="Blue Note", venue_location="123 Main St",
        show_time=datetime.time(20, 0),
    )
    vevent = build_vevent(event)
    assert vevent.get("summary") == "Jazz Night"
    assert vevent.get("uid") is not None
    assert vevent.get("dtstart") is not None
    assert vevent.get("dtend") is not None
    assert "Blue Note" in str(vevent.get("location"))


def test_build_vevent_naive_datetime_by_default():
    """Without timezone, datetimes should be naive."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="V")
    vevent = build_vevent(event)
    dt_val = vevent.get("dtstart").dt
    assert dt_val.tzinfo is None


def test_build_vevent_with_timezone():
    """With timezone, datetimes should be timezone-aware."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="V")
    vevent = build_vevent(event, timezone="America/Chicago")
    dt_val = vevent.get("dtstart").dt
    assert dt_val.tzinfo is not None
    assert str(dt_val.tzinfo) == "America/Chicago"


def test_build_vevent_includes_description_when_present():
    """VEVENT should include description when event has details."""
    event = Event(
        title="Show", date=datetime.date(2025, 6, 15), venue_name="V",
        price="$20", ticket_url="https://example.com",
    )
    vevent = build_vevent(event)
    assert vevent.get("description") is not None
    assert vevent.get("url") is not None


def test_build_vevent_omits_description_when_empty():
    """VEVENT should not include description when event has no details."""
    event = Event(title="Show", date=datetime.date(2025, 6, 15), venue_name="V")
    vevent = build_vevent(event)
    assert vevent.get("description") is None
