# BoardGamePriceTracker

A Python-based scraper that monitors board game deals on Planszeo.pl, fetches additional statistics (rank and rating) from BoardGameGeek (BGG), and sends email notifications for high-quality deals.

## Features

- **Automated Scrapping**: Monitors Planszeo.pl "Okazje" (Deals) section.
- **BGG Integration**: Fetches real-time BGG ratings and ranks for games.
- **Smart Alerts**: Sends email notifications if a game meets certain criteria (e.g., BGG Rank < 200 or BGG Rating > 8.0).
- **History Tracking**: Keeps track of already processed games to avoid duplicate alerts.
- **Data Export**: Saves all scraped deals into a timestamped CSV file for further analysis.
- **GitHub Actions Support**: Ready to run on a schedule using GitHub Actions.

## Requirements

- Python 3.8+
- BGG API Token (Personal Access Token)
- Email account with App Password (for notifications)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/zyngi/BoardGamePriceTracker.git
   cd BoardGamePriceTracker
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory:
   ```env
   BGG_API_TOKEN=your_bgg_api_token
   EMAIL_SENDER=your_email@gmail.com
   EMAIL_APP_PASSWORD=your_app_password
   ```

## Usage

Run the scraper manually:
```bash
python -m src.main
```

The script will:
1. Scrape the latest deals from Planszeo.
2. Fetch details for new games.
3. Check BGG stats.
4. Send emails for top-tier deals.
5. Save results to `data/planszeo_deals_YYYYMMDD_HHMMSS.csv`.

## Testing

To ensure the connections to Planszeo and BGG are working correctly:
```bash
python -m pytest tests/test_connections.py
```

## BGG API Token

As of late 2025, BoardGameGeek requires a Personal Access Token for XML API2 requests.
1. Log in to [BoardGameGeek](https://boardgamegeek.com).
2. Go to your account settings to generate an API Token.
3. Ensure the token is added to your `.env` file or GitHub Secrets.

## Deployment (GitHub Actions)

The project includes a `.github/workflows/scraper.yml` to run the scraper automatically every 6 hours.
Make sure to add the following Secrets to your GitHub repository:
- `BGG_API_TOKEN`
- `EMAIL_SENDER`
- `EMAIL_APP_PASSWORD`

## Project Structure

- `src/`: Core application logic.
  - `main.py`: Entry point.
  - `bgg_api.py`: BGG XML API2 client.
  - `scraper.py`: Planszeo scraper.
  - `notifier.py`: Email notification logic.
  - `config.py`: Configuration and environment variables.
- `tests/`: Connection and unit tests.
- `data/`: Storage for history and CSV exports.
