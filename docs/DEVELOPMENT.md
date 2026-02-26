# Development Documentation

## Project Architecture

The project follows a modular, type-safe architecture using **Pydantic** for data modeling and configuration.

### 1. `src/main.py` (The Orchestrator)
Contains the `BoardGameTracker` class, which orchestrates the entire flow:
- Scrapes new deals from Planszeo.
- Filters out already-seen deals using `data/last_checked_games.json`.
- Enriches deals with details from Planszeo and stats from BGG.
- Evaluates alert criteria and triggers notifications.
- Exports results to CSV.

### 2. `src/models.py` (Data Models)
Defines the core data structures using Pydantic `BaseModel`:
- `PlanszeoDeal`: Basic deal information from the list view.
- `BggStats`: Statistics retrieved from BoardGameGeek.
- `GameDetails`: A combined model containing all available data for a game.

### 3. `src/scraper.py` (Planszeo Service)
Handles HTML parsing of Planszeo.pl using `BeautifulSoup`.
- `get_deals(page_num)` -> `List[PlanszeoDeal]`
- `get_details(deal)` -> `PlanszeoDeal` (enriched)

### 4. `src/bgg_api.py` (BGG Service)
Interacts with the BGG XML API2.
- Uses `Authorization: Bearer <token>` and a unique `User-Agent`.
- `get_stats(bgg_url)` -> `Optional[BggStats]`

### 5. `src/config.py` (Configuration)
Uses `pydantic-settings` to manage environment variables.
- Loads secrets from `.env`.
- Provides a centralized `settings` object with validated configuration.

### 6. `src/notifier.py` & `src/storage.py`
- `EmailNotifier`: Handles SMTP communication.
- `storage`: Simple JSON serialization utilities.

## Adding New Features

### Changing Alert Criteria
Modify the `_check_alerts` method in `BoardGameTracker` (within `src/main.py`). The logic is partitioned into BGG-based and Planszeo-based thresholds.

### Adding New Fields
Update the models in `src/models.py`. Pydantic will automatically handle validation and `model_dump()` for CSV export.

## Continuous Integration

The `.github/workflows/scraper.yml` runs every 6 hours.
**Important**: Ensure the following secrets are configured in GitHub:
- `BGG_API_TOKEN`
- `EMAIL_SENDER`
- `EMAIL_APP_PASSWORD`

## Troubleshooting

- **Validation Errors**: If Planszeo or BGG change their response format, Pydantic might raise a `ValidationError`. Check `src/models.py` and the respective scraper/API service.
- **401 Unauthorized**: Check your `BGG_API_TOKEN`. BGG requires a Personal Access Token.
