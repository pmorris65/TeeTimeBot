"""
Google Sheets config reader for TeeTimeBot.

Reads tee time preferences from a Google Spreadsheet with two sheets/tabs:

Sheet 1 - "Settings":
  | Setting           | Value |
  | Tee Times to Book | 4     |

Sheet 2 - "Preferences":
  | Priority | Time  | Hole | Holes to Play | Transport |
  | 1        | 8:07  | 10   | 18            | CART      |
  | 2        | 8:15  | 10   | 18            | WALK      |
  | ...      | ...   | ...  | ...           | ...       |
"""

import os
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TeeTimePreference:
    """A single tee time preference."""
    priority: int
    time: str
    hole: int
    holes_to_play: int  # 9 or 18
    transport: str  # CART, WALK, or WALK/RIDE


@dataclass
class TeeTimeConfig:
    """Complete configuration from the sheet."""
    tee_times_to_book: int
    preferences: List[TeeTimePreference]


def get_config_from_sheets(spreadsheet_id: str, credentials_json: Optional[str] = None) -> TeeTimeConfig:
    """
    Read tee time configuration from Google Sheets.

    Args:
        spreadsheet_id: The Google Sheet ID (from the URL)
        credentials_json: JSON string of service account credentials.
                         If None, reads from GOOGLE_CREDENTIALS env var.

    Returns:
        TeeTimeConfig with settings and preferences
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    # Get credentials
    if credentials_json is None:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS')

    if not credentials_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable not set")

    # Parse credentials
    creds_dict = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )

    # Build the Sheets API service
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()

    # Read the settings from "Settings" sheet (A:B, skip header)
    settings_result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range='Settings!A2:B10'
    ).execute()
    settings_values = settings_result.get('values', [])

    # Parse tee times to book
    tee_times_to_book = 1  # default
    for row in settings_values:
        if len(row) >= 2 and 'tee times to book' in row[0].lower():
            tee_times_to_book = int(row[1])
            break

    # Read preferences from "Preferences" sheet (A:E, skip header)
    prefs_result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range='Preferences!A2:E20'
    ).execute()
    prefs_values = prefs_result.get('values', [])

    # Parse preferences (header already skipped in query)
    preferences = []
    for row in prefs_values:
        if len(row) >= 4:
            try:
                # Transport defaults to CART if not specified
                transport = str(row[4]).strip().upper() if len(row) >= 5 else "CART"
                # Normalize transport values
                if transport not in ["CART", "WALK", "WALK/RIDE"]:
                    transport = "CART"

                pref = TeeTimePreference(
                    priority=int(row[0]),
                    time=str(row[1]).strip(),
                    hole=int(row[2]),
                    holes_to_play=int(row[3]),
                    transport=transport
                )
                preferences.append(pref)
            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping invalid row {row}: {e}")
                continue

    # Sort by priority
    preferences.sort(key=lambda p: p.priority)

    logger.info(f"Loaded config: book {tee_times_to_book} tee times, {len(preferences)} preferences")

    return TeeTimeConfig(
        tee_times_to_book=tee_times_to_book,
        preferences=preferences
    )


def get_default_config() -> TeeTimeConfig:
    """Return a default config for testing/fallback."""
    return TeeTimeConfig(
        tee_times_to_book=1,
        preferences=[
            TeeTimePreference(priority=1, time="8:07", hole=10, holes_to_play=18, transport="CART")
        ]
    )
