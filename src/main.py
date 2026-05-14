"""Entry point for the Filmhouse Calendar Sync script."""

import os
import sys

from scraper import FilmhouseScraper
from calendar_sync import CalendarSync


def main() -> None:
    """Run the full scrape-and-sync pipeline."""
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    credentials_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")

    if not calendar_id:
        print(
            "Error: GOOGLE_CALENDAR_ID environment variable not set",
            file=sys.stderr,
        )
        sys.exit(1)

    if not credentials_json:
        print(
            "Error: GOOGLE_CALENDAR_CREDENTIALS environment variable not set",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Scraping Filmhouse.sg...")
    scraper = FilmhouseScraper()
    films = scraper.scrape()
    total_screenings = sum(len(f["screenings"]) for f in films)
    print(f"Found {len(films)} films with {total_screenings} screenings")

    if not films:
        print("No screenings found. Exiting.")
        return

    print("Syncing to Google Calendar...")
    sync = CalendarSync(calendar_id, credentials_json)
    stats = sync.sync_screenings(films)

    print(
        f"Done! Created: {stats['created']}, "
        f"Updated: {stats['updated']}, "
        f"Errors: {stats['errors']}"
    )


if __name__ == "__main__":
    main()
