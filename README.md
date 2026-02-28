# Concert Scraper

Automatically scrape local concert venue websites, extract event data using an LLM, and add events to your calendar. Set it up once, schedule it weekly, and never miss a show.

## How It Works

```
Venue website  -->  Scraper (HTTP / Playwright)  -->  LLM extraction  -->  Calendar
                        |                                  |                   |
                   HTML to markdown               Structured JSON         ICS file,
                                                   (Pydantic)         Apple Calendar,
                                                       |              or CalDAV/iCloud
                                                  Multi-day merge
                                                  + deduplication
```

1. **Scrape** -- Fetches each venue's events page via plain HTTP. Falls back to a headless Chromium browser for JavaScript-heavy sites (React, Vue, etc.). If the configured URL 404s, the scraper automatically tries common event page paths (`/events`, `/calendar`, `/shows`, etc.).
2. **Extract** -- Sends the page content (converted to markdown) to an LLM. The LLM returns structured JSON with event details: title, date, times, artists, price, ticket URL.
3. **Merge** -- Consecutive-date events with the same title and venue (e.g., a 3-day festival listed as Fri/Sat/Sun) are merged into a single multi-day calendar block.
4. **Deduplicate** -- A local SQLite database tracks every event that has been added. Events are never added twice, even across runs.
5. **Calendar** -- New events are written to an ICS file, added to Apple Calendar via AppleScript, or pushed to any CalDAV server (including iCloud from Linux).

## Cost

| Component | Cost |
|-----------|------|
| Claude Haiku (default LLM) | ~$0.05/run, ~$2.50/year weekly |
| Ollama (optional local LLM) | $0 -- runs on your hardware |
| Hosting | $0 -- runs on your machine |
| Scheduling | $0 -- cron, systemd, or launchd |

## Platform Support

| Platform | Calendar Backend | Scheduling |
|----------|-----------------|------------|
| macOS | Apple Calendar (auto-detected) | launchd plist |
| Linux | ICS file export (default) or CalDAV | cron or systemd timer |
| Any | CalDAV (opt-in, works with iCloud) | -- |

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/garlockr/concert-scraper.git
cd concert-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure

```bash
cp venues.example.yaml venues.yaml
# Edit venues.yaml -- add your local venues, set your timezone
```

### 3. Set your API key

```bash
# Option A: environment variable
export ANTHROPIC_API_KEY=sk-ant-your-key-here

# Option B: .env file
cp .env.example .env
# Edit .env with your key
```

### 4. Run

```bash
# Preview what would be added (no calendar changes)
concert-scraper scrape --dry-run

# Add events to calendar for real
concert-scraper scrape
```

### Optional extras

```bash
# For JS-heavy venue sites (React, Vue, etc.)
pip install -e ".[browser]"
playwright install chromium

# For CalDAV / iCloud from Linux
pip install -e ".[caldav]"

# For free local LLM instead of Claude
# Install Ollama from https://ollama.com, then:
ollama pull llama3.1
# Set llm_backend: "ollama" in venues.yaml
```

## Configuration

All configuration lives in `venues.yaml`. See [`venues.example.yaml`](venues.example.yaml) for a fully commented template.

### General settings

| Setting | Default | Description |
|---------|---------|-------------|
| `calendar_name` | `"Local Concerts"` | Name of the calendar to create/use |
| `calendar_backend` | `"auto"` | `"auto"`, `"applescript"`, `"caldav"`, or `"ics"` |
| `llm_backend` | `"anthropic"` | `"anthropic"` or `"ollama"` |
| `timezone` | `""` (floating) | IANA timezone, e.g. `"America/Chicago"` |
| `ics_output_dir` | `"output/"` | Directory for ICS file export |
| `db_path` | `"data/events.db"` | SQLite database for dedup tracking |
| `request_delay` | `2` | Seconds between venue requests |
| `default_event_duration_hours` | `3` | Fallback when end time is unknown |

### LLM settings

**Anthropic** (default):
```yaml
anthropic:
  model: "claude-haiku-4-5-20251001"  # cheapest, excellent for extraction
  # model: "claude-sonnet-4-6"        # better quality, ~10x cost
```

**Ollama** (free, local):
```yaml
llm_backend: "ollama"
ollama:
  model: "llama3.1"           # good balance, 8GB RAM
  # model: "qwen2.5:14b"      # better extraction, 16GB RAM
  base_url: "http://localhost:11434"
```

### CalDAV settings

For iCloud access from Linux, generate an app-specific password at [appleid.apple.com](https://appleid.apple.com):

```yaml
calendar_backend: "caldav"
caldav:
  url: "https://caldav.icloud.com"
  username: "your-apple-id@icloud.com"
  password: "your-app-specific-password"
```

### Venue configuration

Each venue entry requires three fields:

```yaml
venues:
  - name: "The Pageant"
    url: "https://www.thepageant.com/events"
    location: "6161 Delmar Blvd, St. Louis, MO 63112"
    requires_browser: false    # optional, default false
```

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable venue name (used in calendar events) |
| `url` | Yes | URL of the venue's events/calendar page |
| `location` | Yes | Street address (shown in calendar event location) |
| `requires_browser` | No | Set `true` for JS-rendered sites. Requires the `browser` extra. |

**Tips for finding the right URL:**
- Look for `/events`, `/calendar`, `/shows`, or `/schedule` on the venue's site
- If `--dry-run` returns no events, try setting `requires_browser: true`
- The scraper auto-tries common event paths if the URL 404s

## CLI Reference

### `concert-scraper scrape`

Scrape all configured venues and add new events to the calendar.

```bash
concert-scraper scrape                              # full run
concert-scraper scrape --dry-run                    # preview only
concert-scraper scrape --venue "The Fillmore"       # single venue
concert-scraper scrape --retry-empty                # only venues with no events in ICS
concert-scraper scrape --dry-run --venue "Venue"    # combine flags
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Preview events without adding to calendar |
| `--venue NAME` | Scrape only the named venue |
| `--retry-empty` | Only scrape venues that have no events in the ICS file yet |

### `concert-scraper list`

Show upcoming events from the local database.

```bash
concert-scraper list
```

### `concert-scraper export`

Export upcoming events to a standalone `.ics` file.

```bash
concert-scraper export                    # default: events.ics
concert-scraper export --output my.ics    # custom path
```

### Global options

```bash
concert-scraper --config path/to/venues.yaml scrape   # custom config file
concert-scraper --log-file path/to/log scrape          # custom log location
concert-scraper -v scrape                              # verbose (logs to terminal)
concert-scraper --version                              # show version
```

## Multi-Day Event Merging

When the LLM extracts a multi-day festival as separate per-day entries (e.g., Friday, Saturday, Sunday), the scraper automatically detects consecutive dates with the same title and venue and merges them into a single calendar event spanning the full date range.

- A 3-day festival becomes one calendar block instead of three separate events
- Weekly residencies (same title every Friday) are **not** merged -- only consecutive dates
- The merged event uses the first day's start time and the last day's end time
- Calendar descriptions show the full date range (e.g., "Multi-day: 2025-06-13 to 2025-06-15")
- Backward compatible with events added before the merge feature

## Deduplication

The scraper tracks every event in a local SQLite database (`data/events.db`). On each run:

- Events already in the database are skipped
- New events are added to both the calendar and the database
- Events older than 90 days are automatically purged from the database
- The dedup key is based on normalized venue name + date + title, so minor title variations (capitalization, punctuation, "The") don't cause duplicates

## Auto-Scheduling

### Linux -- cron

```bash
crontab -e
```

Add:
```
0 9 * * 1 cd ~/Code/concert-scraper && .venv/bin/concert-scraper scrape >> /tmp/concert-scraper.log 2>&1
```

A pre-built cron line is in [`scheduling/concert-scraper.cron`](scheduling/concert-scraper.cron).

### Linux -- systemd timer

```bash
# Edit paths in the service file first
sudo cp scheduling/concert-scraper.service /etc/systemd/system/
sudo cp scheduling/concert-scraper.timer /etc/systemd/system/
sudo systemctl enable --now concert-scraper.timer

# Check status
systemctl status concert-scraper.timer
journalctl -u concert-scraper.service
```

Runs every Monday at 9:00 AM. `Persistent=true` ensures a missed run (e.g., laptop was off) executes on next boot.

### macOS -- launchd

```bash
# Edit the plist: replace YOUR_USERNAME with your username
cp scheduling/com.concert-scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.concert-scraper.plist
```

Logs to `/tmp/concert-scraper.log` and `/tmp/concert-scraper.err`.

## Project Structure

```
concert-scraper/
  src/concert_scraper/
    __init__.py          # package version
    cli.py               # Click CLI commands (scrape, list, export)
    config.py            # YAML config loading + validation
    models.py            # Pydantic models (Event, VenueConfig, AppConfig)
    scraper.py           # HTTP + Playwright page fetching
    extractor.py         # LLM prompt + JSON parsing (Anthropic / Ollama)
    merge.py             # Multi-day event merging
    calendar.py          # Calendar backends (AppleScript, CalDAV, ICS)
    ics.py               # Standalone ICS export
    db.py                # SQLite dedup database
  tests/
    test_models.py       # Event model, normalization, date handling
    test_merge.py        # Multi-day merge logic
    test_calendar.py     # Calendar event building, AppleScript escaping
    test_extractor.py    # LLM prompt formatting, JSON parsing
    test_scraper.py      # URL validation, SPA detection, fallback URLs
    test_db.py           # Database operations
  scheduling/            # cron, systemd, and launchd configs
  venues.example.yaml    # Annotated config template
  .env.example           # API key template
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"
pytest tests/ -v
```

Requires Python 3.12+.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Config file not found" | Copy `venues.example.yaml` to `venues.yaml` |
| "ANTHROPIC_API_KEY not set" | `export ANTHROPIC_API_KEY=sk-ant-...` or switch to Ollama |
| "Calendar permission denied" (macOS) | System Settings > Privacy & Security > Calendar > allow Terminal |
| "Playwright not installed" | `pip install concert-scraper[browser] && playwright install chromium` |
| "Ollama connection refused" | Start Ollama with `ollama serve` |
| "No events found" | Check the venue URL is correct; try `requires_browser: true` |
| "CalDAV authentication failed" | Verify your app-specific password at [appleid.apple.com](https://appleid.apple.com) |
| pip install fails on Python 3.14 | `pip install --only-binary :all: <package>`, or use Python 3.12/3.13 via pyenv |
