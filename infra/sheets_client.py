# infra/sheets_client.py

import gspread
from google.oauth2.service_account import Credentials

from config.settings import (
    SERVICE_ACCOUNT_FILE,
    SCOPES,
    SPREADSHEET_URL,
)


def open_spreadsheet():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    return client.open_by_url(SPREADSHEET_URL)
