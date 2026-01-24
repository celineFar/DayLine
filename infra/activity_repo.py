# infra/activity_repo.py

import gspread
import pandas as pd
from datetime import datetime, timedelta, time

from config.settings import SHEET_NAMES
from infra.sheets_client import open_spreadsheet


def make_columns_unique(cols):
    seen = {}
    out = []
    for c in cols:
        c = c.strip() if c else "Unnamed"
        if c not in seen:
            seen[c] = 0
            out.append(c)
        else:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
    return out


def read_and_clean_sheet(spreadsheet, sheet_name):
    ws = spreadsheet.worksheet(sheet_name)
    values = ws.get("A:I")

    df = pd.DataFrame(values[1:], columns=values[0])
    df.columns = make_columns_unique(df.columns)

    df["Date"] = df["Date"].replace("", pd.NA).ffill()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    df["source"] = sheet_name
    return df


# TODO: handle the error when start and end dates are not within the dates of imported data
def load_activities(start_date=None, end_date=None):
    spreadsheet = open_spreadsheet()
    dfs = [read_and_clean_sheet(spreadsheet, s) for s in SHEET_NAMES]
    df = pd.concat(dfs, ignore_index=True)

    if start_date:
        df = df[df["Date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["Date"] <= pd.to_datetime(end_date)]

    return df.sort_values("Date")


def _get_or_create_sleep_sheet(spreadsheet):
    try:
        return spreadsheet.worksheet("Sleep")
    except gspread.exceptions.WorksheetNotFound:
        return spreadsheet.add_worksheet(
            title="Sleep",
            rows=1000,
            cols=10,
        )


def _split_sleep_across_midnight(start_dt, end_dt):
    """
    Returns a list of (date, start_time, end_time) tuples.
    """
    segments = []

    current_start = start_dt
    while current_start.date() < end_dt.date():
        midnight = datetime.combine(
            current_start.date() + timedelta(days=1),
            time(0, 0),
        )
        segments.append(
            (current_start.date(), current_start.time(), midnight.time())
        )
        current_start = midnight

    segments.append(
        (current_start.date(), current_start.time(), end_dt.time())
    )

    return segments


def append_sleep_record(date, start_time, end_time, user_id=None):
    """
    date: YYYY-MM-DD or date
    start_time, end_time: HH:MM or datetime.time
    """

    spreadsheet = open_spreadsheet()
    sheet = _get_or_create_sleep_sheet(spreadsheet)

    # Normalize inputs
    if isinstance(date, str):
        date = datetime.fromisoformat(date).date()

    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%H:%M").time()

    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, "%H:%M").time()

    start_dt = datetime.combine(date, start_time)

    # Detect crossing midnight
    end_date = date
    if end_time <= start_time:
        end_date = date + timedelta(days=1)

    end_dt = datetime.combine(end_date, end_time)

    rows = []
    for d, s, e in _split_sleep_across_midnight(start_dt, end_dt):
        rows.append([
            d.isoformat(),
            s.strftime("%H:%M:%S"),
            e.strftime("%H:%M:%S"),
            user_id or "",
        ])

    sheet.append_rows(rows, value_input_option="USER_ENTERED")
