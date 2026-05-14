# Filmhouse Calendar Sync

Automatically scrape film screenings from [Filmhouse.sg](https://filmhouse.sg/films/) and sync them to Google Calendar.

## Features

- Daily automated scraping of film screenings
- Extracts film title, duration, rating, genre, director, and cast
- Creates or updates Google Calendar events for each screening
- Deduplication via deterministic event IDs
- Runs daily at 6 AM SGT via GitHub Actions

## Setup

### 1. Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the **Google Calendar API**
4. Create a **Service Account** (IAM & Admin > Service Accounts)
5. Generate a JSON key for the service account
6. Note the service account email (e.g., `service-account@project.iam.gserviceaccount.com`)

### 2. Google Calendar

1. Create a new calendar (or use existing)
2. Go to **Settings and sharing**
3. Under **Share with specific people**, add the service account email with **Make changes to events** permission
4. Copy the **Calendar ID** (found in Settings under "Integrate calendar")

### 3. GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add:

- `GOOGLE_CALENDAR_ID`: Your Google Calendar ID
- `GOOGLE_CALENDAR_CREDENTIALS`: The entire contents of the service account JSON key file

### 4. Local Development

```bash
# Install dependencies
uv sync

# Run scraper
GOOGLE_CALENDAR_ID="your-calendar-id" \
GOOGLE_CALENDAR_CREDENTIALS='{...json...}' \
PYTHONPATH=src uv run python src/main.py
```

## Project Structure

```
src/
├── main.py          # Entry point
├── scraper.py       # Filmhouse.sg scraper
└── calendar_sync.py # Google Calendar API client
.github/
└── workflows/
    └── daily-scrape.yml  # GitHub Actions workflow
```

## How It Works

1. **Scrape**: Uses `scrapling`'s `Fetcher` to retrieve and parse the Filmhouse.sg films page
2. **Parse**: Extracts each film's metadata and all screening dates/times
3. **Sync**: Creates or updates Google Calendar events using a Service Account

Each screening becomes a separate calendar event with:
- Start and end times (based on film duration)
- Film metadata in the description
- Booking link
- Location set to "Filmhouse Cinemas, Singapore"

## Manual Trigger

You can manually run the workflow from the GitHub Actions tab by selecting the **Daily Filmhouse Scrape** workflow and clicking **Run workflow**.
