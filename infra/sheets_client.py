# infra/sheets_client.py

import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    SERVICE_ACCOUNT_FILE,
    SCOPES,
    SPREADSHEET_URL,
)

# Cache the client and spreadsheet to avoid re-authenticating every request
_cached_client = None
_cached_spreadsheet = None


def _get_client():
    """Get or create a cached gspread client."""
    global _cached_client
    if _cached_client is None:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES,
        )
        _cached_client = gspread.authorize(creds)
    return _cached_client


def open_spreadsheet():
    """Get the spreadsheet, using cached connection when possible."""
    global _cached_spreadsheet
    if _cached_spreadsheet is None:
        client = _get_client()
        _cached_spreadsheet = client.open_by_url(SPREADSHEET_URL)
    return _cached_spreadsheet


def invalidate_cache():
    """Clear cached client and spreadsheet (call if auth fails)."""
    global _cached_client, _cached_spreadsheet
    _cached_client = None
    _cached_spreadsheet = None
