from __future__ import annotations

import datetime

from icalendar import Calendar, Event as iCalEvent

from concert_scraper.calendar import _build_description, _build_location
from concert_scraper.models import Event


def export_ics(
    events: list[Event], output_path: str, default_duration_hours: int = 3
) -> None:
    """Export a list of events to a .ics file.

    Args:
        events: List of Event objects to export.
        output_path: File path for the .ics output.
        default_duration_hours: Fallback duration when end_time is unknown.
    """
    cal = Calendar()
    cal.add("prodid", "-//ConcertScraper//EN")
    cal.add("version", "2.0")

    for event in events:
        vevent = iCalEvent()
        vevent.add("summary", event.title)
        vevent.add("dtstart", event.start_datetime)
        vevent.add("dtend", event.end_datetime)
        vevent.add("location", _build_location(event))
        desc = _build_description(event)
        if desc:
            vevent.add("description", desc)
        if event.ticket_url:
            vevent.add("url", event.ticket_url)
        vevent.add("uid", f"{event.normalized_key()}@concert-scraper")
        cal.add_component(vevent)

    with open(output_path, "wb") as f:
        f.write(cal.to_ical())

    print(f"Exported {len(events)} events to {output_path}")
