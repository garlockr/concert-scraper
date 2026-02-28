# Venue Research Plan — St. Louis Metro Area

## Objective

Discover as many live music venues as possible in the greater St. Louis metropolitan area (Missouri + Illinois side). This includes dedicated concert halls, bars with regular live music, breweries, coffee shops, outdoor series, DIY spaces, and any other place that hosts live music events. For each venue, find the events/calendar page URL that the concert-scraper tool can scrape.

## Prerequisites

The git repo must already exist at `/home/rgarlock/Code/concert-scraper/` before this agent starts. If it doesn't, the agent should:
1. `mkdir -p /home/rgarlock/Code/concert-scraper/research`
2. `cd /home/rgarlock/Code/concert-scraper && git init` (if no repo exists yet)

The builder agent may be working in this repo simultaneously. That's fine — the research agent only touches files inside `research/` and the root `venues.yaml`. The builder agent only touches `src/`, `tests/`, `scheduling/`, and config files. No conflicts.

## Output Files

1. **`research/venues_discovered.yaml`** — Every venue found, with metadata and validation status
2. **`research/RESEARCH_PLAN.md`** — This file, with checklists marked as completed
3. **`venues.yaml`** (project root) — Final polished output with only validated, scrapable venues

## Instructions for the Research Agent

- Work through the phases below IN ORDER. Each phase builds on the last.
- After each search or batch of searches, IMMEDIATELY write new venues to `venues_discovered.yaml`. Do not accumulate findings in memory.
- Before adding a venue, check if it already exists in the file (normalize names: lowercase, strip "the", strip punctuation). If it exists, UPDATE the entry with any new info rather than creating a duplicate.
- Mark each checklist item `[x]` as you complete it.
- For every venue, try to find the SPECIFIC events/calendar page URL, not just the homepage.
- If a venue only posts events on Facebook/Instagram, still record it with `events_source: facebook` — it's useful data even if it can't be auto-scraped yet.
- When fetching a page, extract just the venue names and URLs. Don't paste raw HTML into your context.
- If a search yields no new results, note that and move on. Don't retry the same search.

## Venue Entry Template

Every venue in `venues_discovered.yaml` should follow this format:

```yaml
- name: "Venue Name"
  neighborhood: "Neighborhood or City"
  website: "https://venue-website.com"
  events_url: "https://venue-website.com/events"
  events_source: "own_website"  # own_website | facebook | instagram | eventbrite | bandsintown | songkick | do314 | other
  requires_browser: false  # true if events page is JS-rendered, false if static HTML, null if unknown
  address: "123 Main St, St. Louis, MO 63101"
  venue_type: "bar"  # concert_hall | theater | bar | brewery | coffee_shop | park | community_center | record_store | gallery | restaurant | diy | church | other
  capacity: ""  # approximate, leave empty if unknown
  found_via: "Phase 1 - Do314"
  status: "discovered"  # discovered | validated | ready | facebook_only | no_events_page | dead_link | permanently_closed
  notes: ""
```

## Stopping Criteria

The research is complete when:
- All Phase 1-5 checklists are marked `[x]`
- At least 60 unique venues have been cataloged in `venues_discovered.yaml`
- Phase 6 validation has been run on all discovered venues
- `venues.yaml` has been generated with all `status: ready` venues

---

## Phase 1: Anchor Sources (High-Yield Aggregators)

These sources already curate St. Louis venue/event data. Start here to build the baseline.

- [x] **Do314.com** — Search for "Do314 venues" or "Do314.com St. Louis venues". This is THE local events aggregator. Try to find their venue directory page and extract all venue names.
- [x] **Riverfront Times (RFT)** — Search "Riverfront Times St. Louis music venues" and "Riverfront Times best live music St. Louis". RFT is the alt-weekly and publishes venue guides.
- [x] **STL Today / St. Louis Post-Dispatch** — Search "STL Today live music venues guide"
- [x] **Wikipedia** — Search "List of music venues in St. Louis" or "Music of St. Louis" Wikipedia page
- [x] **General web search** — "St. Louis concert venues complete list"
- [x] **General web search** — "St. Louis live music venues 2025 2026"
- [x] **General web search** — "best live music venues St. Louis Missouri"

**After Phase 1:** You should have 25-40 venues. If you have fewer than 20, do additional general searches before proceeding.

---

## Phase 2: Aggregator Platform Deep-Dives

Search specific event platforms for St. Louis venues.

- [x] **Eventbrite** — Search "Eventbrite St. Louis music concerts" — note which unique venues host events
- [x] **Bandsintown** — Search "Bandsintown St. Louis venues" or "Bandsintown concerts St. Louis"
- [x] **Songkick** — Search "Songkick St. Louis venues"
- [x] **JamBase** — Search "JamBase St. Louis concerts venues"

**After Phase 2:** Cross-reference with Phase 1 results. Add any new venues found.

---

## Phase 3: Neighborhood Sweeps

St. Louis has distinct neighborhoods, each with their own music scenes. Search for live music in each.

### Tier 1 — Core Music Neighborhoods (search all of these)

- [x] **The Loop / Delmar Blvd / University City** — "The Loop St. Louis live music bars"
- [x] **The Grove (Manchester Ave)** — "The Grove St. Louis live music"
- [x] **Cherokee Street** — "Cherokee Street St. Louis live music venues"
- [x] **Soulard** — "Soulard St. Louis live music bars" (big bar district)
- [x] **South Grand** — "South Grand St. Louis live music"
- [x] **Downtown / Washington Ave** — "Downtown St. Louis live music concerts"
- [x] **Grand Center / Midtown** — "Grand Center St. Louis music venues" (arts district — Sheldon, KMOX area)
- [x] **Laclede's Landing** — "Laclede's Landing St. Louis live music"

### Tier 2 — Secondary Neighborhoods (search these next)

- [x] **Maplewood** — "Maplewood MO live music"
- [x] **Webster Groves** — "Webster Groves live music bars"
- [x] **Benton Park / Tower Grove** — "Benton Park Tower Grove live music"
- [x] **Central West End** — "Central West End St. Louis live music"
- [x] **The Hill** — "The Hill St. Louis live music"
- [x] **Clayton** — "Clayton MO live music"
- [x] **Dogtown** — "Dogtown St. Louis live music"

### Tier 3 — Suburbs and Metro East (Illinois side)

- [x] **St. Charles / St. Peters** — "St. Charles MO live music venues"
- [x] **Kirkwood / Sunset Hills** — "Kirkwood MO live music"
- [x] **Belleville, IL** — "Belleville IL live music"
- [x] **Collinsville / Edwardsville, IL** — "Collinsville IL live music venues" (note: The Gateway Classic Cars area, old Pop's location)
- [x] **East St. Louis / Sauget, IL** — "Sauget IL concerts" / "East St. Louis music venues"
- [x] **Maryland Heights** — "Maryland Heights MO concerts" (Hollywood Casino Amphitheatre area)
- [x] **Chesterfield / Wildwood** — "Chesterfield MO live music"

**After Phase 3:** You should have found many small bars and breweries not on the aggregator sites.

---

## Phase 4: Venue Type Sweeps

Search for specific types of venues that host music.

- [x] **Breweries** — "St. Louis breweries with live music"
- [x] **Coffee shops** — "St. Louis coffee shops live music open mic"
- [x] **Outdoor/Parks** — "St. Louis outdoor concert series 2026" / "St. Louis parks live music summer"
- [x] **Record stores** — "St. Louis record stores in-store performances"
- [x] **Wineries** — "St. Louis area wineries live music" (Missouri wine country is nearby)
- [x] **Churches/Community** — "St. Louis church concert series" / "St. Louis community center music"
- [x] **Hotels/Lounges** — "St. Louis hotel bar live music jazz"
- [x] **Restaurants** — "St. Louis restaurants live music"
- [x] **VFW/Elks/Legion** — "St. Louis VFW live music" / "American Legion St. Louis concerts"
- [x] **Art galleries** — "St. Louis art gallery music events"
- [x] **Casinos** — "St. Louis area casino concerts" (Lumiere, Hollywood, River City)

---

## Phase 5: Community & Underground Sources

Catch the long tail of DIY, house show, and community venues.

- [x] **Reddit r/StLouis** — Search "r/StLouis live music" / "r/StLouis concert venues" / "r/StLouis best bars for music"
- [x] **Reddit r/StLouis** — Search "r/StLouis hidden gem music" / "r/StLouis local bands where to see"
- [x] **General search** — "St. Louis DIY music scene venues"
- [x] **General search** — "St. Louis underground music venues"
- [x] **General search** — "St. Louis jazz clubs" (STL has a rich jazz history)
- [x] **General search** — "St. Louis blues clubs" (birthplace of blues — National Blues Museum area)
- [x] **General search** — "St. Louis punk venues" / "St. Louis metal venues"
- [x] **General search** — "new music venues St. Louis 2025 2026" (catch recently opened spots)

---

## Phase 6: Validation Pass

For EVERY venue in `venues_discovered.yaml`, perform these checks:

### 6a. Website Validation
- [x] For each venue with a website, fetch the homepage and verify it loads
- [x] Find the specific events/calendar page URL (not just the homepage)
- [x] If the events page exists, check if it contains actual event listings
- [x] If the events page appears to be JS-rendered (empty body, SPA shell), mark `requires_browser: true`
- [x] If the website is dead (404, domain expired), mark `status: dead_link`

### 6b. Facebook-Only Venues
- [x] For venues with no website, search "{venue name} St. Louis facebook" to find their Facebook page
- [x] Record the Facebook URL in the `website` field
- [x] Mark `events_source: facebook` and `status: facebook_only`

### 6c. Address Verification
- [x] For venues missing an address, search "{venue name} St. Louis address"
- [x] Verify the address looks correct (right neighborhood, not a residential address for a concert hall, etc.)

### 6d. Closure Check
- [x] Search for any venues that might be permanently closed: "{venue name} St. Louis closed"
- [x] Mark closed venues as `status: permanently_closed`

---

## Phase 7: Generate Final Output

After validation is complete:

1. Filter `venues_discovered.yaml` to only venues with `status: validated` or `status: ready`
2. These venues must have a working `events_url` that the scraper can access
3. Generate `venues.yaml` in the project root using the concert-scraper config format:

```yaml
calendar_name: "STL Concerts"
calendar_backend: "auto"
llm_backend: "anthropic"
anthropic:
  model: "claude-haiku-4-5-20251001"
db_path: "data/events.db"
request_delay: 2
default_event_duration_hours: 3
ics_output_dir: "output/"
venues:
  - name: "Venue Name"
    url: "https://venue.com/events"
    location: "123 Main St, St. Louis, MO 63101"
    requires_browser: false
  # ... more venues
```

4. Also generate a summary at the bottom of this file:
   - Total venues discovered: X
   - Validated & scrapable: X
   - Facebook-only (manual check needed): X
   - Dead links / closed: X
   - No events page found: X

5. **Commit and push the research findings:**
   ```bash
   cd /home/rgarlock/Code/concert-scraper
   git add research/venues_discovered.yaml research/RESEARCH_PLAN.md venues.yaml
   git commit -m "research: add St. Louis venue discovery results

   Discovered X venues across the STL metro area.
   Y venues validated and scrapable, Z Facebook-only, W closed/dead.

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
   git push
   ```
   If push fails because the builder agent has pushed first, do `git pull --rebase` then push again. There should be no conflicts since these files don't overlap with the builder's files.

---

## Sanity Check — Expected Major Venues

If your research does NOT find these well-known STL venues, something went wrong. Go back and search specifically for any missing ones:

- The Pageant
- Delmar Hall
- The Factory
- Stifel Theatre
- Chaifetz Arena
- Enterprise Center
- Hollywood Casino Amphitheatre
- The Sheldon Concert Hall
- Off Broadway
- Blueberry Hill (The Duck Room)
- Old Rock House
- Red Flag
- The Ready Room (may be closed — verify)
- Fubar (may be closed — verify)
- The Firebird (may be closed — verify)
- BB's Jazz, Blues & Soups
- Broadway Oyster Bar
- The Focal Point
- The Improv Shop (comedy but sometimes music)
- The Muny (outdoor musical theater — seasonal)
- Powell Hall (St. Louis Symphony)
- The Fox Theatre
- Chesterfield Amphitheater
- Soldiers Memorial (occasional concerts)

This list is NOT exhaustive — it's a minimum sanity check.

---

## Research Summary (completed 2026-02-27)

- **Total venues discovered:** 63
- **Validated & scrapable (in venues.yaml):** 51
- **Facebook-only (manual check needed):** 2 (CBGB, The Haunt)
- **Dead links / permanently closed:** 5 (Fubar, The Ready Room, The Firebird, 2720 Cherokee, Pop's old location)
- **No events page found:** 1 (The Lux)
- **Other (not in venues.yaml but validated):** 4 (Atomic Cowboy, The Improv Shop, Vintage Vinyl, Whitaker Music Festival)

### Sanity Check Results
All 24 expected major venues were found and verified:
- The Ready Room: CONFIRMED CLOSED (COVID 2020, briefly reopened, closed again)
- Fubar: CONFIRMED CLOSED (Feb 2020, replaced by Red Flag)
- The Firebird: CONFIRMED CLOSED (per Yelp Jan 2026)
- Soldiers Memorial: Not found as regular music venue (occasional events only)
- All other expected venues: FOUND and VALIDATED

### Notable Discoveries Beyond Expected List
- The Sovereign (opened Sept 2025 in Grand Center, by Old Rock House team)
- The Golden Record (newer venue at 2720 Cherokee, replaced 2720 Cherokee PAC)
- The Hawthorn (opened 2022, 1300 cap mid-size hall downtown)
- Mississippi Underground (10,000 sq ft EDM warehouse)
- City Winery St. Louis (opened March 2023 at City Foundry)
- The Attic Music Bar, The Hi-Hat, Platypus, Sinkhole, and many more small venues
