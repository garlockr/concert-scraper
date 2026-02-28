from __future__ import annotations

import datetime

from concert_scraper.merge import merge_multiday_events
from concert_scraper.models import Event


def _event(title: str, date: datetime.date, venue: str = "Venue",
           end_time: datetime.time | None = None,
           show_time: datetime.time | None = None) -> Event:
    """Helper to create a minimal Event."""
    return Event(title=title, date=date, venue_name=venue,
                 end_time=end_time, show_time=show_time)


class TestMergeConsecutive:
    """Consecutive-date events with same venue+title should merge."""

    def test_three_day_festival(self):
        events = [
            _event("Fest", datetime.date(2025, 6, 13)),
            _event("Fest", datetime.date(2025, 6, 14)),
            _event("Fest", datetime.date(2025, 6, 15)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 1
        assert merged[0].date == datetime.date(2025, 6, 13)
        assert merged[0].end_date == datetime.date(2025, 6, 15)

    def test_two_day_event(self):
        events = [
            _event("Show", datetime.date(2025, 7, 4)),
            _event("Show", datetime.date(2025, 7, 5)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 1
        assert merged[0].end_date == datetime.date(2025, 7, 5)

    def test_preserves_first_day_times(self):
        events = [
            _event("Fest", datetime.date(2025, 6, 13),
                   show_time=datetime.time(18, 0)),
            _event("Fest", datetime.date(2025, 6, 14),
                   show_time=datetime.time(14, 0)),
        ]
        merged = merge_multiday_events(events)
        assert merged[0].show_time == datetime.time(18, 0)

    def test_uses_last_day_end_time(self):
        events = [
            _event("Fest", datetime.date(2025, 6, 13),
                   end_time=datetime.time(22, 0)),
            _event("Fest", datetime.date(2025, 6, 14),
                   end_time=datetime.time(23, 0)),
        ]
        merged = merge_multiday_events(events)
        assert merged[0].end_time == datetime.time(23, 0)


class TestNonConsecutive:
    """Non-consecutive dates should NOT merge."""

    def test_gap_in_dates(self):
        events = [
            _event("Show", datetime.date(2025, 6, 13)),
            _event("Show", datetime.date(2025, 6, 15)),  # gap on 14th
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 2
        assert merged[0].end_date is None
        assert merged[1].end_date is None

    def test_weekly_residency(self):
        """Same title every Friday should not merge."""
        events = [
            _event("Jazz Night", datetime.date(2025, 6, 6)),
            _event("Jazz Night", datetime.date(2025, 6, 13)),
            _event("Jazz Night", datetime.date(2025, 6, 20)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 3


class TestDifferentGrouping:
    """Different titles or venues should not merge."""

    def test_different_titles(self):
        events = [
            _event("Show A", datetime.date(2025, 6, 13)),
            _event("Show B", datetime.date(2025, 6, 14)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 2

    def test_different_venues(self):
        events = [
            _event("Fest", datetime.date(2025, 6, 13), venue="Venue A"),
            _event("Fest", datetime.date(2025, 6, 14), venue="Venue B"),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 2


class TestMixedScenarios:
    """Mixed single-day and multi-day events in the same batch."""

    def test_mixed_merge(self):
        events = [
            _event("Fest", datetime.date(2025, 6, 13)),
            _event("Fest", datetime.date(2025, 6, 14)),
            _event("Fest", datetime.date(2025, 6, 15)),
            _event("One-Off", datetime.date(2025, 6, 14)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 2
        fest = [e for e in merged if e.title == "Fest"][0]
        oneoff = [e for e in merged if e.title == "One-Off"][0]
        assert fest.end_date == datetime.date(2025, 6, 15)
        assert oneoff.end_date is None

    def test_two_separate_runs_same_title(self):
        """Two non-adjacent runs of the same title should produce two events."""
        events = [
            _event("Show", datetime.date(2025, 6, 13)),
            _event("Show", datetime.date(2025, 6, 14)),
            # gap
            _event("Show", datetime.date(2025, 6, 20)),
            _event("Show", datetime.date(2025, 6, 21)),
        ]
        merged = merge_multiday_events(events)
        assert len(merged) == 2
        assert merged[0].end_date == datetime.date(2025, 6, 14)
        assert merged[1].end_date == datetime.date(2025, 6, 21)

    def test_single_event_passthrough(self):
        events = [_event("Solo", datetime.date(2025, 7, 1))]
        merged = merge_multiday_events(events)
        assert len(merged) == 1
        assert merged[0].end_date is None

    def test_empty_list(self):
        assert merge_multiday_events([]) == []

    def test_output_sorted_by_date(self):
        events = [
            _event("Late", datetime.date(2025, 7, 10)),
            _event("Early", datetime.date(2025, 6, 1)),
        ]
        merged = merge_multiday_events(events)
        assert merged[0].date < merged[1].date
