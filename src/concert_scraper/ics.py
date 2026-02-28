from __future__ import annotations

import logging

from icalendar import Calendar

from concert_scraper.calendar import build_vevent
from concert_scraper.models import Event

logger = logging.getLogger(__name__)


def export_ics(
    events: list[Event], output_path: str, default_duration_hours: int = 3,
    timezone: str = "",
) -> None:
    """Export a list of events to a .ics file.

    Args:
        events: List of Event objects to export.
        output_path: File path for the .ics output.
        default_duration_hours: Fallback duration when end_time is unknown.
        timezone: IANA timezone name (e.g. "America/Chicago").
    """
    cal = Calendar()
    cal.add("prodid", "-//ConcertScraper//EN")
    cal.add("version", "2.0")

    for event in events:
        cal.add_component(build_vevent(event, timezone=timezone))

    with open(output_path, "wb") as f:
        f.write(cal.to_ical())

    logger.info("Exported %d events to %s", len(events), output_path)
