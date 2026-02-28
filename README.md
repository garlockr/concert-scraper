# Concert Scraper

Automatically scrape local concert venue websites, extract event data using an LLM, and add events to your calendar.

## Cost Breakdown

| Component | Cost |
|-----------|------|
| Ollama (optional LLM) | $0 -- runs locally |
| Claude Haiku (default LLM) | ~$0.05/run, ~$2.50/year weekly |
| Hosting | $0 -- runs on your machine |
| Scheduling | $0 -- cron/systemd (Linux) or launchd (macOS) |
| All dependencies | $0 -- open source |

## Platform Support

| Platform | Calendar Backend | Scheduling |
|----------|-----------------|------------|
| macOS | AppleScript (auto-detected) | launchd plist |
| Linux | ICS file export (default) or CalDAV for iCloud | cron or systemd timer |
| Any | CalDAV (opt-in, works with iCloud) | -- |

## Quick Start

1. Clone the repo:
   ```bash
   git clone https://github.com/garlockr/concert-scraper.git
   cd concert-scraper
   ```

2. Copy and customize the config:
   ```bash
   cp venues.example.yaml venues.yaml
   # Edit venues.yaml with your local venues
   ```

3. Create a virtual environment and install:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

4. Set your Anthropic API key (default LLM backend):
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

5. (Optional) If any venues need JavaScript rendering:
   ```bash
   pip install -e ".[browser]"
   playwright install chromium
   ```

6. (Optional) If using CalDAV/iCloud from Linux:
   ```bash
   pip install -e ".[caldav]"
   ```
   Then configure CalDAV credentials in `venues.yaml`.

7. (Optional) To use Ollama instead of Claude (free, no API key):
   ```bash
   # Install Ollama from https://ollama.com
   ollama pull llama3.1
   ```
   Then set `llm_backend: "ollama"` in `venues.yaml`.

8. Test with a dry run:
   ```bash
   concert-scraper scrape --dry-run
   ```

9. Run for real:
   ```bash
   concert-scraper scrape
   ```

## Configuration

All configuration lives in `venues.yaml`. See `venues.example.yaml` for a fully commented template.

Key settings:

- **calendar_backend**: `"auto"` (default -- AppleScript on macOS, ICS on Linux), `"applescript"`, `"caldav"`, or `"ics"`
- **llm_backend**: `"anthropic"` (default) or `"ollama"`
- **anthropic.model**: `"claude-haiku-4-5-20251001"` (cheapest, recommended) or `"claude-sonnet-4-6"`
- **ollama.model**: `"llama3.1"` (default) or `"qwen2.5:14b"` for better quality
- **ics_output_dir**: Directory for exported `.ics` files (default: `output/`)
- **request_delay**: Seconds between venue requests (default: 2)
- **default_event_duration_hours**: Fallback duration when end time is unknown (default: 3)

### Venue Configuration

Each venue needs:
- **name**: Human-readable venue name
- **url**: URL of their events/calendar page
- **location**: Street address (used in calendar events)
- **requires_browser**: Set to `true` for JS-heavy sites (requires `pip install concert-scraper[browser]`)

## CLI Commands

```bash
# Full scrape + calendar add
concert-scraper scrape

# Preview without adding to calendar
concert-scraper scrape --dry-run

# Scrape a single venue
concert-scraper scrape --venue "The Fillmore"

# Show upcoming events from database
concert-scraper list

# Export to .ics file
concert-scraper export --output events.ics

# Use a different config file
concert-scraper --config my-venues.yaml scrape
```

## Auto-Scheduling

### Linux (cron)

```bash
crontab -e
# Add this line:
0 9 * * 1 cd ~/Code/concert-scraper && .venv/bin/concert-scraper scrape >> /tmp/concert-scraper.log 2>&1
```

### Linux (systemd timer)

```bash
sudo cp scheduling/concert-scraper.service /etc/systemd/system/
sudo cp scheduling/concert-scraper.timer /etc/systemd/system/
sudo systemctl enable --now concert-scraper.timer
```

### macOS (launchd)

```bash
# Edit the plist to set your username
cp scheduling/com.concert-scraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.concert-scraper.plist
```

## Adding Venues

1. Find the venue's events/calendar page URL
2. Add an entry to `venues.yaml`:
   ```yaml
   - name: "My Local Venue"
     url: "https://example.com/events"
     location: "123 Main St, City, ST 12345"
     requires_browser: false
   ```
3. Test with: `concert-scraper scrape --venue "My Local Venue" --dry-run`
4. If no events are found and the site uses JavaScript, set `requires_browser: true`

## Troubleshooting

- **"Config file not found"** -- Copy `venues.example.yaml` to `venues.yaml` and customize it.
- **"Calendar permission denied" (macOS)** -- System Settings > Privacy > Calendar > Allow Terminal.
- **"Playwright not installed"** -- Run `pip install concert-scraper[browser] && playwright install chromium`.
- **"Ollama connection refused"** -- Start Ollama with `ollama serve`.
- **"No events found"** -- Try `--dry-run` to see raw output; check the venue URL is correct.
- **"CalDAV authentication failed"** -- Verify your app-specific password at https://appleid.apple.com.
- **"ANTHROPIC_API_KEY not set"** -- Run `export ANTHROPIC_API_KEY=sk-ant-...` or switch to Ollama.
- **pip install fails on Python 3.14** -- Try `pip install --only-binary :all: <package>`. If that fails, consider using Python 3.12 or 3.13 via pyenv.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
pip install pytest pytest-asyncio
python3 -m pytest tests/ -v
```
