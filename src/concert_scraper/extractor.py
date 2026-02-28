from __future__ import annotations

import datetime
import json
import logging
import os
import re

import httpx

from concert_scraper.models import AppConfig, Event

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are an event extraction assistant. Given the text content of a concert venue's events page, extract ALL upcoming events into structured JSON.

Today's date is {today}. Use this to resolve relative dates like "this Saturday" or "next Friday".

The venue is: {venue_name}
The venue location is: {venue_location}

Extract each event as a JSON object with these fields:
- title (string): The event name or headlining artist/band
- date (string): Date in YYYY-MM-DD format
- doors_time (string or null): Door opening time in HH:MM 24-hour format
- show_time (string or null): Show start time in HH:MM 24-hour format
- end_time (string or null): End time in HH:MM 24-hour format, if listed
- artists (array of strings): All performing artists/bands listed for this event
- price (string or null): Ticket price as displayed (e.g., "$25", "Free", "$20-$40")
- ticket_url (string or null): Direct URL to purchase tickets
- description (string or null): Brief description if available

Rules:
- Only include events dated today ({today}) or later
- If only one time is given with no label, treat it as show_time
- If a time is labeled "Doors" or "Doors open", it is doors_time
- Do not invent or hallucinate events — only extract what is on the page
- If a date is ambiguous, use context clues and today's date to resolve it
- For multi-day festivals, create one entry per day
- Ignore non-music events (comedy, trivia, private events) UNLESS they could plausibly be music-related
- Return an empty array if no upcoming events are found

Return ONLY a JSON array of event objects. No markdown fences, no explanation."""


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _format_prompt(venue_name: str, venue_location: str) -> str:
    """Format the extraction prompt with today's date and venue info."""
    today = datetime.date.today().isoformat()
    return EXTRACTION_PROMPT.format(
        today=today,
        venue_name=venue_name,
        venue_location=venue_location,
    )


async def extract_via_ollama(
    markdown: str, venue_name: str, venue_location: str, config: AppConfig
) -> list[dict]:
    """Extract events using a local Ollama LLM."""
    prompt = _format_prompt(venue_name, venue_location)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": markdown},
    ]

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{config.ollama.base_url}/api/chat",
            json={
                "model": config.ollama.model,
                "messages": messages,
                "format": "json",
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")

    content = _strip_markdown_fences(content)

    try:
        result = json.loads(content)
        if isinstance(result, dict) and "events" in result:
            result = result["events"]
        if not isinstance(result, list):
            raise ValueError("Expected a JSON array")
        return result
    except (json.JSONDecodeError, ValueError):
        # Retry once
        messages.append({"role": "assistant", "content": content})
        messages.append(
            {
                "role": "user",
                "content": "Your response was not valid JSON. Please return ONLY a JSON array of events.",
            }
        )
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{config.ollama.base_url}/api/chat",
                json={
                    "model": config.ollama.model,
                    "messages": messages,
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")

        content = _strip_markdown_fences(content)
        result = json.loads(content)
        if isinstance(result, dict) and "events" in result:
            result = result["events"]
        return result if isinstance(result, list) else []


async def extract_via_anthropic(
    markdown: str, venue_name: str, venue_location: str, config: AppConfig
) -> list[dict]:
    """Extract events using Anthropic Claude API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "Anthropic SDK not installed. Install with: pip install anthropic"
        )

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set.\n"
            "Set it with: export ANTHROPIC_API_KEY=<your-key>\n"
            "Or switch to Ollama by setting llm_backend: 'ollama' in venues.yaml"
        )

    prompt = _format_prompt(venue_name, venue_location)

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=config.anthropic.model,
        max_tokens=8192,
        system=prompt,
        messages=[{"role": "user", "content": markdown}],
    )

    content = response.content[0].text
    content = _strip_markdown_fences(content)

    try:
        result = json.loads(content)
    except json.JSONDecodeError as e:
        logger.debug("Raw Anthropic response (first 500 chars): %s", content[:500])
        # Try to extract JSON array from the response with a regex
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Failed to parse Anthropic response as JSON: %s", e)
                return []
        else:
            logger.warning("No JSON array found in Anthropic response: %s", e)
            return []

    if isinstance(result, dict) and "events" in result:
        result = result["events"]
    return result if isinstance(result, list) else []


async def extract_events(
    markdown: str, venue_name: str, venue_location: str, config: AppConfig
) -> list[Event]:
    """Extract events from markdown text using the configured LLM backend.

    Returns a list of valid Event objects; invalid events are logged and skipped.
    """
    if config.llm_backend == "ollama":
        raw_events = await extract_via_ollama(markdown, venue_name, venue_location, config)
    else:
        raw_events = await extract_via_anthropic(markdown, venue_name, venue_location, config)

    events: list[Event] = []
    for i, raw in enumerate(raw_events):
        try:
            # Sanitize string values from LLM output: strip control chars
            for key, val in raw.items():
                if isinstance(val, str):
                    raw[key] = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", val)
                elif isinstance(val, list):
                    raw[key] = [
                        re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", v)
                        if isinstance(v, str) else v
                        for v in val
                    ]
            raw["venue_name"] = venue_name
            raw["venue_location"] = venue_location
            event = Event(**raw)
            events.append(event)
        except Exception as exc:
            logger.warning("Skipping invalid event %d: %s — %s", i, raw.get("title", "?"), exc)

    return events
