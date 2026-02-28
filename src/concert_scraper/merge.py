from __future__ import annotations

import datetime
from collections import defaultdict

from concert_scraper.models import Event, _normalize


def merge_multiday_events(events: list[Event]) -> list[Event]:
    """Merge consecutive-date events with the same venue and title.

    Groups events by (venue_name, normalized_title), sorts each group by date,
    and collapses consecutive-date runs into a single Event with end_date set.
    Single-day events and non-consecutive same-title events pass through unchanged.
    """
    # Group by (venue_name, normalized_title)
    groups: dict[tuple[str, str], list[Event]] = defaultdict(list)
    for event in events:
        key = (event.venue_name, _normalize(event.title))
        groups[key].append(event)

    result: list[Event] = []
    for group_events in groups.values():
        sorted_events = sorted(group_events, key=lambda e: e.date)
        result.extend(_merge_consecutive_runs(sorted_events))

    # Preserve a stable ordering: sort by (date, venue, title)
    result.sort(key=lambda e: (e.date, e.venue_name, e.title))
    return result


def _merge_consecutive_runs(sorted_events: list[Event]) -> list[Event]:
    """Given events sorted by date (same venue+title), merge consecutive runs."""
    if not sorted_events:
        return []

    merged: list[Event] = []
    run_start = sorted_events[0]
    run_end = sorted_events[0]

    for event in sorted_events[1:]:
        if event.date == run_end.date + datetime.timedelta(days=1):
            # Consecutive — extend the run
            run_end = event
        else:
            # Gap — flush the current run and start a new one
            merged.append(_flush_run(run_start, run_end))
            run_start = event
            run_end = event

    # Flush the final run
    merged.append(_flush_run(run_start, run_end))
    return merged


def _flush_run(first: Event, last: Event) -> Event:
    """Produce a single Event from a consecutive run.

    If the run is a single day, returns the event unchanged.
    Otherwise, returns a copy of the first event with end_date and
    end_time taken from the last event.
    """
    if first.date == last.date:
        return first
    return first.model_copy(
        update={"end_date": last.date, "end_time": last.end_time}
    )
