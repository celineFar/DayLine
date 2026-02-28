# infra/sheets_client.py

import logging

import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    SERVICE_ACCOUNT_FILE,
    SCOPES,
    SPREADSHEET_URL,
)

logger = logging.getLogger(__name__)

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
    """
    Get the spreadsheet, reconnecting if the cached connection has gone stale.
    On any failure, resets both caches and retries once from scratch.
    """
    global _cached_client, _cached_spreadsheet
    if _cached_spreadsheet is not None:
        return _cached_spreadsheet

    try:
        client = _get_client()
        _cached_spreadsheet = client.open_by_url(SPREADSHEET_URL)
        return _cached_spreadsheet
    except Exception as first_err:
        logger.warning("Spreadsheet open failed (%s), resetting connection and retrying.", first_err)
        _cached_client = None
        _cached_spreadsheet = None

    # One retry with a fresh client
    client = _get_client()
    _cached_spreadsheet = client.open_by_url(SPREADSHEET_URL)
    return _cached_spreadsheet


def invalidate_cache():
    """Clear cached client and spreadsheet (call if auth fails)."""
    global _cached_client, _cached_spreadsheet
    _cached_client = None
    _cached_spreadsheet = None
