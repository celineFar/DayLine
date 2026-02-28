# config/settings.py

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _require_env(name: str) -> str:
    """Get required environment variable or raise an error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


# Credentials - loaded from environment variables
TELEGRAM_BOT_TOKEN = _require_env("TELEGRAM_BOT_TOKEN")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
SPREADSHEET_URL = _require_env("SPREADSHEET_URL")

# Sheet configuration
SHEET_NAMES = ["Work", "Thesis", "Extra", "Sleep", "Activities"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Time constants
DAY_MINUTES = 1440
MAX_SLEEP_START = 4 * 60  # 04:00

SLEEP_REMINDER_DELAY = timedelta(
    seconds=int(os.getenv("SLEEP_REMINDER_SECONDS", 10 * 60 * 60))  # Default: 10 hours
)

IDLE_REMINDER_INTERVAL = timedelta(
    seconds=int(os.getenv("IDLE_REMINDER_SECONDS", 10 * 60))  # Default: 10 minutes
)

MAX_SNOOZE_HOURS = 12
