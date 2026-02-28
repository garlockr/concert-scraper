from __future__ import annotations

import datetime
import re
import sys
from typing import Literal

from pydantic import BaseModel, SecretStr, computed_field, field_validator


def _normalize(text: str) -> str:
    """Normalize a string for deduplication: lowercase, strip 'the ', remove
    non-alphanumeric characters, and collapse whitespace."""
    t = text.lower().strip()
    t = re.sub(r"^the\s+", "", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class Event(BaseModel):
    """A single concert/event extracted from a venue page."""

    title: str
    date: datetime.date
    end_date: datetime.date | None = None
    doors_time: datetime.time | None = None
    show_time: datetime.time | None = None
    end_time: datetime.time | None = None
    artists: list[str] = []
    price: str | None = None
    ticket_url: str | None = None
    description: str | None = None
    venue_name: str
    venue_location: str | None = None
    default_duration_hours: int = 3

    @computed_field  # type: ignore[prop-decorator]
    @property
    def start_datetime(self) -> datetime.datetime:
        """Combine date with the best available start time.
        Prefers show_time, then doors_time, then defaults to 20:00."""
        if self.show_time:
            t = self.show_time
        elif self.doors_time:
            t = self.doors_time
        else:
            t = datetime.time(20, 0)
        return datetime.datetime.combine(self.date, t)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def end_datetime(self) -> datetime.datetime:
        """Return end time on the last day of the event, or start + default duration.
        For multi-day events, the end time is on end_date instead of date.
        If end_time crosses midnight (before start), rolls to the next day."""
        last_day = self.end_date or self.date
        if self.end_time:
            end = datetime.datetime.combine(last_day, self.end_time)
            if end <= datetime.datetime.combine(last_day, self.start_datetime.time()):
                end += datetime.timedelta(days=1)
            return end
        return datetime.datetime.combine(
            last_day, self.start_datetime.time()
        ) + datetime.timedelta(hours=self.default_duration_hours)

    def normalized_key(self) -> str:
        """Return a dedup key: venue|date_or_range|normalized_title.
        Multi-day events use 'start..end' for the date portion."""
        if self.end_date and self.end_date != self.date:
            date_part = f"{self.date.isoformat()}..{self.end_date.isoformat()}"
        else:
            date_part = self.date.isoformat()
        return f"{self.venue_name}|{date_part}|{_normalize(self.title)}"

    def covered_day_keys(self) -> list[str]:
        """Return individual-day dedup keys for each day this event covers.
        Used for backward-compat: detecting pre-merge individual-day entries."""
        norm_title = _normalize(self.title)
        last = self.end_date or self.date
        keys = []
        d = self.date
        while d <= last:
            keys.append(f"{self.venue_name}|{d.isoformat()}|{norm_title}")
            d += datetime.timedelta(days=1)
        return keys


class VenueConfig(BaseModel):
    """Configuration for a single venue to scrape."""

    name: str
    url: str
    location: str
    requires_browser: bool = False

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Venue URL must use http or https, got: {parsed.scheme!r}")
        return v


class OllamaConfig(BaseModel):
    """Ollama LLM configuration."""

    model: str = "llama3.1"
    base_url: str = "http://localhost:11434"


class AnthropicConfig(BaseModel):
    """Anthropic Claude LLM configuration."""

    model: str = "claude-haiku-4-5-20251001"


class CaldavConfig(BaseModel):
    """CalDAV connection configuration."""

    url: str = "https://caldav.icloud.com"
    username: str = ""
    password: SecretStr = SecretStr("")


class AppConfig(BaseModel):
    """Top-level application configuration loaded from venues.yaml."""

    calendar_name: str = "Local Concerts"
    calendar_backend: Literal["auto", "applescript", "caldav", "ics"] = "auto"
    caldav: CaldavConfig | None = None
    ics_output_dir: str = "output/"
    llm_backend: Literal["ollama", "anthropic"] = "anthropic"
    ollama: OllamaConfig = OllamaConfig()
    anthropic: AnthropicConfig = AnthropicConfig()
    db_path: str = "data/events.db"
    request_delay: int = 2
    default_event_duration_hours: int = 3
    timezone: str = ""
    venues: list[VenueConfig] = []

    def resolved_calendar_backend(self) -> str:
        """Resolve 'auto' to the platform-appropriate backend."""
        if self.calendar_backend != "auto":
            return self.calendar_backend
        if sys.platform == "darwin":
            return "applescript"
        return "ics"
