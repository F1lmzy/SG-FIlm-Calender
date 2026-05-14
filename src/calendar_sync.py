"""Google Calendar API client for syncing film screenings."""

import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class CalendarSync:
    """Sync film screenings to Google Calendar."""

    SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
    DEFAULT_LOCATION = "Filmhouse Cinemas, Singapore"
    TIMEZONE = "Asia/Singapore"

    def __init__(self, calendar_id: str, credentials_json: str) -> None:
        self.calendar_id = calendar_id
        self.credentials = self._load_credentials(credentials_json)
        self.service = build("calendar", "v3", credentials=self.credentials)

    def _load_credentials(self, credentials_json: str):
        """Load service account credentials from JSON string."""
        info = json.loads(credentials_json)
        return service_account.Credentials.from_service_account_info(
            info, scopes=self.SCOPES
        )

    def sync_screenings(self, films: List[Dict]) -> Dict[str, int]:
        """Sync all screenings, returning operation stats."""
        stats = {"created": 0, "updated": 0, "errors": 0}

        for film in films:
            for screening in film["screenings"]:
                try:
                    self._sync_single_screening(film, screening, stats)
                except HttpError as exc:
                    stats["errors"] += 1
                    print(f"Error syncing screening: {exc}")

        return stats

    def _sync_single_screening(
        self, film: Dict, screening: Dict, stats: Dict[str, int]
    ) -> None:
        """Create or update a single screening event."""
        event_id = self._generate_event_id(film["title"], screening["start"])
        event_body = self._build_event(film, screening, event_id)

        try:
            self.service.events().insert(
                calendarId=self.calendar_id, body=event_body
            ).execute()
            stats["created"] += 1
        except HttpError as exc:
            if exc.resp.status == 409:
                self.service.events().update(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                    body=event_body,
                ).execute()
                stats["updated"] += 1
            else:
                raise

    def _generate_event_id(self, title: str, start: datetime) -> str:
        """Generate a deterministic event ID for deduplication."""
        raw = f"{title}_{start.isoformat()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _build_event(self, film: Dict, screening: Dict, event_id: str) -> Dict:
        """Build a Google Calendar event body."""
        return {
            "id": event_id,
            "summary": film["title"],
            "description": self._build_description(film, screening),
            "start": {
                "dateTime": screening["start"].isoformat(),
                "timeZone": self.TIMEZONE,
            },
            "end": {
                "dateTime": screening["end"].isoformat(),
                "timeZone": self.TIMEZONE,
            },
            "location": self.DEFAULT_LOCATION,
        }

    def _build_description(self, film: Dict, screening: Dict) -> str:
        """Build event description text."""
        parts = [f"Duration: {film['duration_mins']} minutes"]

        if film.get("rating"):
            parts.append(f"Rating: {film['rating']}")
        if film.get("genre"):
            parts.append(f"Genre: {film['genre']}")
        if film.get("director"):
            parts.append(f"Director: {film['director']}")
        if film.get("cast"):
            parts.append(f"Cast: {film['cast']}")
        if screening.get("booking_url"):
            parts.append(f"Book tickets: {screening['booking_url']}")

        return "\n".join(parts)
