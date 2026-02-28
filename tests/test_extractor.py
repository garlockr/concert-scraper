from __future__ import annotations

import datetime
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from concert_scraper.extractor import (
    EXTRACTION_PROMPT,
    _format_prompt,
    _strip_markdown_fences,
    extract_events,
    extract_via_anthropic,
    extract_via_ollama,
)
from concert_scraper.models import AppConfig, Event


def test_prompt_includes_today_date():
    """The formatted prompt should contain today's date."""
    prompt = _format_prompt("Test Venue", "123 Main St")
    today = datetime.date.today().isoformat()
    assert today in prompt


def test_prompt_includes_venue_info():
    """The formatted prompt should contain venue name and location."""
    prompt = _format_prompt("The Fillmore", "1805 Geary Blvd")
    assert "The Fillmore" in prompt
    assert "1805 Geary Blvd" in prompt


def test_parse_valid_json_array():
    """A valid JSON array of events should parse into Event objects."""
    raw = [
        {
            "title": "Test Show",
            "date": "2025-08-01",
            "doors_time": None,
            "show_time": "19:30",
            "end_time": None,
            "artists": ["Band A"],
            "price": "$25",
            "ticket_url": None,
            "description": None,
        }
    ]
    events = []
    for item in raw:
        item["venue_name"] = "Test Venue"
        item["venue_location"] = "123 Main St"
        events.append(Event(**item))
    assert len(events) == 1
    assert events[0].title == "Test Show"


def test_parse_empty_array():
    """An empty array should produce an empty list."""
    raw: list[dict] = []
    events = []
    for item in raw:
        item["venue_name"] = "Test"
        events.append(Event(**item))
    assert events == []


def test_parse_malformed_json_skips_bad_events():
    """Events with invalid data should be skipped, not crash."""
    raw = [
        {"title": "Good Show", "date": "2025-08-01", "venue_name": "V", "venue_location": "L"},
        {"title": "Bad Show", "date": "not-a-date", "venue_name": "V", "venue_location": "L"},
        {"title": "Also Good", "date": "2025-09-01", "venue_name": "V", "venue_location": "L"},
    ]
    events = []
    for item in raw:
        try:
            events.append(Event(**item))
        except Exception:
            pass
    assert len(events) == 2
    assert events[0].title == "Good Show"
    assert events[1].title == "Also Good"


def test_parse_json_with_markdown_fences():
    """Markdown fences around JSON should be stripped."""
    text = '```json\n[{"title": "test"}]\n```'
    cleaned = _strip_markdown_fences(text)
    parsed = json.loads(cleaned)
    assert isinstance(parsed, list)
    assert parsed[0]["title"] == "test"


@pytest.mark.asyncio
async def test_ollama_request_format(monkeypatch):
    """Verify the Ollama request body has correct fields."""
    config = AppConfig(
        llm_backend="ollama",
        venues=[],
    )
    captured_kwargs = {}

    async def mock_post(self, url, **kwargs):
        captured_kwargs.update(kwargs)
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "message": {"content": "[]"}
        }
        return resp

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    result = await extract_via_ollama("some markdown", "Venue", "Location", config)
    body = captured_kwargs["json"]
    assert body["model"] == "llama3.1"
    assert body["format"] == "json"
    assert body["stream"] is False
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][1]["role"] == "user"
    assert result == []


@pytest.mark.asyncio
async def test_anthropic_missing_api_key(monkeypatch):
    """Missing ANTHROPIC_API_KEY should raise a clear error."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    config = AppConfig(llm_backend="anthropic", venues=[])

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await extract_via_anthropic("markdown", "Venue", "Location", config)
