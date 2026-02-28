from __future__ import annotations

import datetime
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar as iCalendar
from icalendar import Event as iCalEvent

from concert_scraper.models import AppConfig, Event

logger = logging.getLogger(__name__)


def build_location(event: Event) -> str:
    """Build location string with venue name and address."""
    if event.venue_location:
        return f"{event.venue_name} — {event.venue_location}"
    return event.venue_name


def build_description(event: Event) -> str:
    """Build a human-readable description string for an event."""
    parts: list[str] = []
    if event.doors_time:
        parts.append(f"Doors: {event.doors_time.strftime('%I:%M %p')}")
    if event.price:
        parts.append(f"Price: {event.price}")
    if event.artists:
        parts.append(f"Artists: {', '.join(event.artists)}")
    if event.description:
        parts.append(event.description)
    if event.ticket_url:
        parts.append(f"Tickets: {event.ticket_url}")
    return "\n".join(parts) if parts else ""


def build_vevent(event: Event, timezone: str = "") -> iCalEvent:
    """Build an iCalendar VEVENT component from an Event.

    Args:
        event: The concert event.
        timezone: IANA timezone name (e.g. "America/Chicago"). If empty,
                  datetimes are stored as naive (floating) times.
    """
    vevent = iCalEvent()
    vevent.add("summary", event.title)

    start = event.start_datetime
    end = event.end_datetime
    if timezone:
        tz = ZoneInfo(timezone)
        start = start.replace(tzinfo=tz)
        end = end.replace(tzinfo=tz)

    vevent.add("dtstart", start)
    vevent.add("dtend", end)
    vevent.add("location", build_location(event))
    desc = build_description(event)
    if desc:
        vevent.add("description", desc)
    if event.ticket_url:
        vevent.add("url", event.ticket_url)
    vevent.add("uid", f"{event.normalized_key()}@concert-scraper")
    return vevent


def add_event(event: Event, config: AppConfig) -> bool:
    """Add an event to the calendar using the configured backend.

    Returns True on success, False on failure. Never raises.
    """
    try:
        backend = config.resolved_calendar_backend()
        if backend == "applescript":
            return _applescript_add_event(event, config.calendar_name)
        elif backend == "caldav":
            return _caldav_add_event(event, config)
        elif backend == "ics":
            return _ics_add_event(event, config)
        else:
            logger.error("Unknown calendar backend: %s", backend)
            return False
    except Exception as exc:
        logger.error("Failed to add event '%s' to calendar: %s", event.title, exc)
        return False


def ensure_calendar(config: AppConfig) -> None:
    """Ensure the target calendar exists, creating it if needed."""
    backend = config.resolved_calendar_backend()
    if backend == "applescript":
        _applescript_ensure_calendar(config.calendar_name)
    elif backend == "caldav":
        _caldav_ensure_calendar(config)
    elif backend == "ics":
        _ics_ensure_calendar(config)


# ---------------------------------------------------------------------------
# AppleScript backend (macOS only)
# ---------------------------------------------------------------------------


def _escape_applescript(s: str) -> str:
    """Escape a string for safe inclusion in AppleScript.

    Strips control characters (newlines, carriage returns, null bytes, tabs)
    that could break out of a quoted string context, then escapes backslashes
    and double quotes.
    """
    # Remove characters that can break AppleScript string context
    s = s.replace("\x00", "")   # null bytes
    s = s.replace("\r\n", " ")  # CRLF → space
    s = s.replace("\r", " ")    # CR → space
    s = s.replace("\n", " ")    # LF → space
    s = s.replace("\t", " ")    # tab → space
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _format_applescript_date(dt: datetime.datetime) -> str:
    """Format a datetime for AppleScript date literal."""
    return dt.strftime("%B %d, %Y at %I:%M:%S %p")


def _applescript_ensure_calendar(calendar_name: str) -> None:
    """Create the calendar in Apple Calendar if it doesn't exist."""
    if sys.platform != "darwin":
        raise RuntimeError("AppleScript backend requires macOS")

    name = _escape_applescript(calendar_name)
    script = f'''
    tell application "Calendar"
        if not (exists calendar "{name}") then
            make new calendar with properties {{name:"{name}"}}
        end if
    end tell
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False, timeout=30)


def _applescript_add_event(event: Event, calendar_name: str) -> bool:
    """Add an event to Apple Calendar via AppleScript."""
    if sys.platform != "darwin":
        raise RuntimeError("AppleScript backend requires macOS")

    cal = _escape_applescript(calendar_name)
    summary = _escape_applescript(event.title)
    location = _escape_applescript(build_location(event))
    description = _escape_applescript(build_description(event))
    start_str = _format_applescript_date(event.start_datetime)
    end_str = _format_applescript_date(event.end_datetime)

    script = f'''
    tell application "Calendar"
        tell calendar "{cal}"
            make new event with properties {{summary:"{summary}", start date:date "{start_str}", end date:date "{end_str}", location:"{location}", description:"{description}"}}
        end tell
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode != 0:
        logger.error("AppleScript error: %s", result.stderr.strip())
        return False
    return True


# ---------------------------------------------------------------------------
# CalDAV backend (cross-platform — works with iCloud from Linux)
# ---------------------------------------------------------------------------


def _caldav_ensure_calendar(config: AppConfig) -> None:
    """Find or create the calendar on the CalDAV server."""
    try:
        import caldav
    except ImportError:
        raise ImportError(
            "CalDAV library not installed. Install with: pip install concert-scraper[caldav]"
        )

    if not config.caldav:
        raise RuntimeError(
            "CalDAV backend requires caldav settings in venues.yaml"
        )

    client = caldav.DAVClient(
        url=config.caldav.url,
        username=config.caldav.username,
        password=config.caldav.password.get_secret_value(),
    )
    principal = client.principal()
    calendars = principal.calendars()

    for cal in calendars:
        if cal.name == config.calendar_name:
            return  # already exists

    principal.make_calendar(name=config.calendar_name)


def _caldav_add_event(event: Event, config: AppConfig) -> bool:
    """Add an event to the CalDAV calendar."""
    try:
        import caldav
    except ImportError:
        raise ImportError(
            "CalDAV library not installed. Install with: pip install concert-scraper[caldav]"
        )

    if not config.caldav:
        raise RuntimeError("CalDAV backend requires caldav settings in venues.yaml")

    client = caldav.DAVClient(
        url=config.caldav.url,
        username=config.caldav.username,
        password=config.caldav.password.get_secret_value(),
    )
    principal = client.principal()
    calendars = principal.calendars()
    target_cal = None
    for cal in calendars:
        if cal.name == config.calendar_name:
            target_cal = cal
            break

    if target_cal is None:
        logger.error("Calendar '%s' not found on CalDAV server", config.calendar_name)
        return False

    ical = iCalendar()
    ical.add("prodid", "-//ConcertScraper//EN")
    ical.add("version", "2.0")
    ical.add_component(build_vevent(event, timezone=config.timezone))
    target_cal.save_event(ical.to_ical().decode("utf-8"))
    return True


# ---------------------------------------------------------------------------
# ICS file export backend (universal — default on Linux)
# ---------------------------------------------------------------------------


def _ics_ensure_calendar(config: AppConfig) -> None:
    """Create the output directory if it doesn't exist."""
    os.makedirs(config.ics_output_dir, exist_ok=True)


def _ics_add_event(event: Event, config: AppConfig) -> bool:
    """Append an event to the running .ics file."""
    output_dir = Path(config.ics_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ics_path = output_dir / f"{config.calendar_name}.ics"

    if ics_path.exists():
        with open(ics_path, "rb") as f:
            cal = iCalendar.from_ical(f.read())
        # Rebuild into a fresh calendar preserving existing events
        new_cal = iCalendar()
        new_cal.add("prodid", "-//ConcertScraper//EN")
        new_cal.add("version", "2.0")
        for component in cal.walk():
            if component.name == "VEVENT":
                new_cal.add_component(component)
        cal = new_cal
    else:
        cal = iCalendar()
        cal.add("prodid", "-//ConcertScraper//EN")
        cal.add("version", "2.0")

    cal.add_component(build_vevent(event, timezone=config.timezone))

    # Atomic write: write to temp file then rename to avoid partial writes
    fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".ics.tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(cal.to_ical())
        os.replace(tmp_path, ics_path)
    except BaseException:
        os.unlink(tmp_path)
        raise

    logger.info("Event written to %s", ics_path)
    return True
