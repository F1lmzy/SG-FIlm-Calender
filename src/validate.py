#!/usr/bin/env python3
"""Validate Google Calendar API credentials and setup before running the full sync."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone


def check_env_vars() -> bool:
    """Check that required environment variables are set."""
    print("=" * 60)
    print("STEP 1: Checking Environment Variables")
    print("=" * 60)

    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID")
    credentials_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")

    issues = []

    if not calendar_id:
        issues.append("  MISSING: GOOGLE_CALENDAR_ID is not set")
    else:
        print(f"  OK: GOOGLE_CALENDAR_ID is set")
        if "@group.calendar.google.com" not in calendar_id and calendar_id != "primary":
            print(f"  WARNING: Calendar ID format looks unusual: {calendar_id}")
            print(f"    Expected format: xxxxxxxxxxx@group.calendar.google.com")

    if not credentials_json:
        issues.append("  MISSING: GOOGLE_CALENDAR_CREDENTIALS is not set")
    else:
        print(f"  OK: GOOGLE_CALENDAR_CREDENTIALS is set ({len(credentials_json)} chars)")

    if issues:
        for issue in issues:
            print(issue)
        print("\n  FIX: Set these as GitHub Secrets or export them in your shell:")
        print("    export GOOGLE_CALENDAR_ID='your-calendar-id'")
        print("    export GOOGLE_CALENDAR_CREDENTIALS='{...json...}'")
        return False

    return True


def validate_credentials_json() -> tuple[bool, dict]:
    """Validate that credentials JSON is parseable and has required fields."""
    print("\n" + "=" * 60)
    print("STEP 2: Validating Credentials JSON")
    print("=" * 60)

    credentials_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")

    try:
        data = json.loads(credentials_json)
    except json.JSONDecodeError as e:
        print(f"  FAILED: Invalid JSON - {e}")
        print("  FIX: Make sure you pasted the ENTIRE contents of the .json key file")
        return False, {}

    required_fields = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
    ]
    missing = [f for f in required_fields if f not in data]

    if missing:
        print(f"  FAILED: Missing required fields: {', '.join(missing)}")
        print("  FIX: Download a fresh JSON key from Google Cloud Console")
        return False, {}

    if data.get("type") != "service_account":
        print(f"  FAILED: Expected type 'service_account', got '{data.get('type')}'")
        print("  FIX: You need a Service Account key, not an OAuth client ID")
        return False, {}

    print(f"  OK: Valid service account JSON")
    print(f"  Project: {data.get('project_id')}")
    print(f"  Client Email: {data.get('client_email')}")
    print(f"  Key ID: {data.get('private_key_id')}")

    return True, data


def test_api_connection(credentials_json: str, calendar_id: str) -> bool:
    """Test that we can authenticate and access the calendar."""
    print("\n" + "=" * 60)
    print("STEP 3: Testing Google Calendar API Connection")
    print("=" * 60)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        print("  FAILED: google-auth or google-api-python-client not installed")
        print("  FIX: Run 'uv sync' to install dependencies")
        return False

    try:
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        service = build("calendar", "v3", credentials=credentials)
        print("  OK: Authenticated successfully")
    except Exception as e:
        print(f"  FAILED: Authentication error - {e}")
        return False

    # Try to get calendar info
    try:
        cal = service.calendars().get(calendarId=calendar_id).execute()
        print(f"  OK: Calendar access confirmed")
        print(f"  Calendar Name: {cal.get('summary')}")
        print(f"  Time Zone: {cal.get('timeZone')}")
    except HttpError as e:
        status = e.resp.status
        if status == 404:
            print(f"  FAILED: Calendar not found (404)")
            print(f"  FIX: Check that the Calendar ID is correct")
        elif status == 403:
            print(f"  FAILED: Permission denied (403)")
            print(f"  FIX: Share the calendar with the service account:")
            print(f"    {info.get('client_email')}")
            print(f"  Go to Calendar Settings > Share with specific people")
        else:
            print(f"  FAILED: HTTP {status} - {e}")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

    # Test creating a dummy event
    print("\n" + "-" * 60)
    print("  STEP 3a: Creating test event...")
    try:
        now = datetime.now(timezone.utc)
        test_event = {
            "summary": "[TEST] Filmhouse Scraper Validation",
            "description": "This is a test event. It will be deleted automatically.",
            "start": {
                "dateTime": now.isoformat(),
                "timeZone": "Asia/Singapore",
            },
            "end": {
                "dateTime": (now + timedelta(minutes=1)).isoformat(),
                "timeZone": "Asia/Singapore",
            },
        }

        created = (
            service.events()
            .insert(calendarId=calendar_id, body=test_event)
            .execute()
        )
        event_id = created["id"]
        print(f"  OK: Test event created (ID: {event_id})")

        # Clean up the test event
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"  OK: Test event deleted")

    except HttpError as e:
        print(f"  FAILED: Could not create event - HTTP {e.resp.status}")
        return False
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

    return True


def main() -> int:
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("  FILMHOUSE CALENDAR SYNC - VALIDATION")
    print("=" * 60)

    # Step 1: Environment variables
    if not check_env_vars():
        return 1

    # Step 2: Credentials JSON
    ok, credentials_data = validate_credentials_json()
    if not ok:
        return 1

    # Step 3: API connection
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "")
    credentials_json = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")

    if not test_api_connection(credentials_json, calendar_id):
        return 1

    print("\n" + "=" * 60)
    print("  ALL CHECKS PASSED!")
    print("=" * 60)
    print("  Your setup is ready. You can now run:")
    print("    PYTHONPATH=src uv run python src/main.py")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
