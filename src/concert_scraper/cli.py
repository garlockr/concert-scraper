from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import click


def _load_dotenv(env_path: Path | None = None) -> None:
    """Load .env file if it exists.

    Args:
        env_path: Explicit path to .env file. If None, looks next to this
                  source file (project root), NOT cwd, to avoid loading
                  arbitrary .env files when invoked from untrusted directories.
    """
    if env_path is None:
        # Resolve relative to the package install location (project root)
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes (single or double)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ.setdefault(key, value)

from concert_scraper import __version__
from concert_scraper.config import load_config
from concert_scraper import db as db_mod
from concert_scraper import calendar as cal_mod
from concert_scraper import scraper
from concert_scraper import extractor
from concert_scraper.ics import export_ics
from concert_scraper.models import Event


def _setup_logging(log_file: str, verbose: bool) -> None:
    """Configure file and optional console logging."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("concert_scraper")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    if verbose:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        root.addHandler(ch)


@click.group()
@click.option("--config", "config_path", default="venues.yaml", help="Path to config file")
@click.option("--log-file", default="logs/scraper.log", help="Path to log file")
@click.option("-v", "--verbose", is_flag=True, help="Also print log messages to terminal")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context, config_path: str, log_file: str, verbose: bool) -> None:
    """Concert Scraper -- Scrape venue websites and add events to your calendar."""
    _load_dotenv()
    _setup_logging(log_file, verbose)
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


@main.command()
@click.option("--dry-run", is_flag=True, help="Preview events without adding to calendar")
@click.option("--venue", "venue_filter", default=None, help="Scrape only this venue (by name)")
@click.option("--retry-empty", is_flag=True, help="Only scrape venues with no events in the ICS file")
@click.pass_context
def scrape_cmd(ctx: click.Context, dry_run: bool, venue_filter: str | None, retry_empty: bool) -> None:
    """Scrape venues and add events to calendar."""
    asyncio.run(_scrape_async(ctx.obj["config_path"], dry_run, venue_filter, retry_empty))


# Register the command under the name "scrape"
scrape_cmd.name = "scrape"


logger = logging.getLogger(__name__)


def _venues_with_events(config) -> set[str]:
    """Read the ICS file and return the set of venue names that have events."""
    ics_path = Path(config.ics_output_dir) / f"{config.calendar_name}.ics"
    if not ics_path.exists():
        return set()
    try:
        from icalendar import Calendar
        with open(ics_path, "rb") as f:
            cal = Calendar.from_ical(f.read())
        venues = set()
        for comp in cal.walk():
            if comp.name == "VEVENT":
                uid = str(comp.get("uid", ""))
                # UID format: venue_name|date|title@concert-scraper
                if "|" in uid:
                    venues.add(uid.split("|")[0])
        return venues
    except Exception as exc:
        logger.warning("Could not read ICS file for --retry-empty: %s", exc)
        return set()


async def _scrape_async(config_path: str, dry_run: bool, venue_filter: str | None, retry_empty: bool = False) -> None:
    """Core async scrape logic."""
    try:
        config = load_config(config_path)
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    if not config.venues:
        click.echo("No venues configured. Edit venues.yaml to add venues.")
        return

    db_mod.init_db(config.db_path)

    if not dry_run:
        try:
            cal_mod.ensure_calendar(config)
        except Exception as exc:
            click.echo(f"[ERROR] Failed to set up calendar: {exc}", err=True)
            sys.exit(1)

    venues = config.venues
    if venue_filter:
        venues = [v for v in venues if v.name.lower() == venue_filter.lower()]
        if not venues:
            click.echo(f"Venue '{venue_filter}' not found in config.", err=True)
            sys.exit(1)

    if retry_empty:
        have_events = _venues_with_events(config)
        venues = [v for v in venues if v.name not in have_events]
        click.echo(f"Retrying {len(venues)} venues with no events in ICS file.")
        if not venues:
            click.echo("All venues already have events.")
            return

    added = 0
    skipped = 0

    for i, venue in enumerate(venues):
        click.echo(f"Scraping {venue.name}...")
        logger.info("Scraping %s (%s)", venue.name, venue.url)
        try:
            markdown = await scraper.scrape(venue.url, venue.requires_browser)
        except Exception as exc:
            click.echo(f"  [ERROR] Failed to scrape {venue.name}: {exc}", err=True)
            logger.error("Failed to scrape %s (%s): %s", venue.name, venue.url, exc)
            continue

        logger.info("Got %d chars of markdown from %s", len(markdown), venue.name)
        click.echo("  Extracting events...")
        try:
            events = await extractor.extract_events(
                markdown, venue.name, venue.location, config
            )
        except Exception as exc:
            click.echo(f"  [ERROR] Failed to extract events from {venue.name}: {exc}", err=True)
            logger.error("Failed to extract events from %s: %s", venue.name, exc)
            continue

        logger.info("Extracted %d events from %s", len(events), venue.name)
        if not events:
            click.echo("  No upcoming events found.")
        else:
            for event in events:
                key = event.normalized_key()
                if db_mod.is_seen(config.db_path, key):
                    click.echo(f"  [SKIP] {event.title} on {event.date} (already added)")
                    skipped += 1
                    continue

                if dry_run:
                    click.echo(
                        f"  [DRY RUN] Would add: {event.title} on {event.date}"
                        f" at {event.show_time or event.doors_time or '20:00'}"
                    )
                    added += 1
                    continue

                success = cal_mod.add_event(event, config)
                if success:
                    db_mod.mark_seen(
                        config.db_path,
                        key,
                        venue.name,
                        event.title,
                        event.date.isoformat(),
                        event_json=event.model_dump_json(),
                    )
                    click.echo(f"  [ADDED] {event.title} on {event.date}")
                    added += 1
                else:
                    click.echo(f"  [ERROR] Failed to add {event.title} to calendar", err=True)

        # Delay between venues (skip after the last one)
        if i < len(venues) - 1:
            time.sleep(config.request_delay)

    action = "Would add" if dry_run else "Added"
    click.echo(f"Done. {action} {added} new events, skipped {skipped} duplicates.")
    logger.info("Run complete. %s %d new events, skipped %d duplicates.", action, added, skipped)


@main.command(name="list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List upcoming events from the database."""
    try:
        config = load_config(ctx.obj["config_path"])
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    db_mod.init_db(config.db_path)
    upcoming = db_mod.get_upcoming(config.db_path)

    if not upcoming:
        click.echo("No upcoming events in database.")
        return

    click.echo(f"{'Date':<12} {'Venue':<25} {'Event'}")
    click.echo("-" * 70)
    for row in upcoming:
        click.echo(f"{row['event_date']:<12} {row['venue_name']:<25} {row['event_title']}")


@main.command()
@click.option("--output", default="events.ics", help="Output .ics file path")
@click.pass_context
def export(ctx: click.Context, output: str) -> None:
    """Export upcoming events to an .ics file."""
    try:
        config = load_config(ctx.obj["config_path"])
    except FileNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    db_mod.init_db(config.db_path)
    upcoming = db_mod.get_upcoming(config.db_path)

    if not upcoming:
        click.echo("No upcoming events to export.")
        return

    import datetime as dt
    import json

    events = []
    for row in upcoming:
        if row.get("event_json"):
            try:
                events.append(Event.model_validate_json(row["event_json"]))
                continue
            except Exception:
                pass
        # Fallback for events stored before event_json was added
        events.append(
            Event(
                title=row["event_title"],
                date=dt.date.fromisoformat(row["event_date"]),
                venue_name=row["venue_name"],
                default_duration_hours=config.default_event_duration_hours,
            )
        )

    export_ics(events, output, config.default_event_duration_hours)
