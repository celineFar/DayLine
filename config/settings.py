# config/settings.py

SERVICE_ACCOUNT_FILE = "timeline-482211-e978bbf1dd0b.json"

# SPREADSHEET_URL = (
#     "https://docs.google.com/spreadsheets/d/"
#     "1c2HXhQJjaTUb-KyRJczOOvpibVAekM_xKvmjK2bDWf0/edit"
# )

SPREADSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1m-UEmHicPNo793ddSdToBydFsV42WsRhcUzQy9SqLXA/edit?gid=0#gid=0"
)


# SHEET_NAMES = ["Work", "Thesis", "Extra"]
SHEET_NAMES = ["Work", "Thesis", "Extra", "Sleep"]


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DAY_MINUTES = 1440
MAX_SLEEP_START = 4 * 60  # 04:00

TELEGRAM_BOT_TOKEN = "8513105895:AAH2n86RKKu01ypbgwLE80iygjgeBjR5VMQ"


from datetime import timedelta
import os

SLEEP_REMINDER_DELAY = timedelta(
    # seconds=int(os.getenv("SLEEP_REMINDER_SECONDS", 10 * 60 * 60))
    seconds= 60 * 10
)
