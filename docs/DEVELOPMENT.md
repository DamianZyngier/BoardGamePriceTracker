# Development Documentation

## Project Architecture

The project is structured into several modular components:

### 1. `src/main.py`
The orchestrator. It manages the scraping loop, checks for new games against the history, fetches additional BGG stats, and triggers notifications.

### 2. `src/scraper.py`
Handles all interactions with Planszeo.pl. It uses `BeautifulSoup` to parse HTML. 
- `get_deals(page_num)`: Extracts basic game info from the "Okazje" list.
- `get_details(planszeo_url)`: Navigates to a specific game page to extract the BGG link and local Planszeo rankings.

### 3. `src/bgg_api.py`
Interacts with the BoardGameGeek XML API2. 
- **Important**: It requires a unique `User-Agent` and an `Authorization: Bearer <token>` header to bypass Cloudflare security.
- Handles `202 Accepted` responses from BGG (which indicate the request is being processed) by retrying after a short delay.

### 4. `src/notifier.py`
Simple SMTP client for sending emails. It uses `smtplib` and requires an SSL connection on port 465.

### 5. `src/config.py`
Centralized configuration. It loads environment variables and defines static constants like URLs and default headers.

### 6. `src/storage.py`
Utility for saving and loading JSON state files (e.g., `game_history.json`).

## Adding New Features

### How to add a new Notifier?
1. Create a new class in `src/notifier.py` or a new file.
2. Implement a `send(subject, body)` method.
3. Update `src/main.py` to initialize and use the new notifier.

### How to change alert criteria?
Alert logic is currently located in `src/main.py` within the processing loop. Look for the "BGG Alert Logic" and "Planszeo Alert Logic" sections to modify thresholds for ratings or ranks.

## Continuous Integration

GitHub Actions is configured to:
- Run on a cron schedule (every 6 hours).
- Use a cache for the `data/` directory to maintain history across runs.
- Authenticate using repository secrets.

## Troubleshooting

- **401 Unauthorized (BGG)**: Ensure your `BGG_API_TOKEN` is valid and the `User-Agent` is unique.
- **202 Accepted (BGG)**: This is normal behavior for BGG. The script will retry automatically.
- **Empty Results (Planszeo)**: Planszeo often changes its HTML structure. If `get_deals` returns 0 items, check if the CSS classes in `src/scraper.py` need updating.
