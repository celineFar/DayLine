# infra/activity_repo.py

import logging
import gspread
import pandas as pd
from datetime import datetime, timedelta, time

from config.settings import SHEET_NAMES
from infra.sheets_client import open_spreadsheet

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 300  # 5 minutes

# Cache storage
_activities_cache = None
_cache_timestamp = None


def _is_cache_valid():
    """Check if cache exists and hasn't expired."""
    if _activities_cache is None or _cache_timestamp is None:
        return False
    age = (datetime.now() - _cache_timestamp).total_seconds()
    return age < CACHE_TTL_SECONDS


def invalidate_activities_cache():
    """Clear the activities cache (call after writing new data)."""
    global _activities_cache, _cache_timestamp
    _activities_cache = None
    _cache_timestamp = None
    logger.debug("Activities cache invalidated")


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


def _load_all_activities():
    """Load all activities from sheets (internal, for caching)."""
    global _activities_cache, _cache_timestamp

    if _is_cache_valid():
        logger.debug("Using cached activities data")
        return _activities_cache

    logger.debug("Fetching activities from Google Sheets")
    spreadsheet = open_spreadsheet()
    dfs = []
    for s in SHEET_NAMES:
        try:
            dfs.append(read_and_clean_sheet(spreadsheet, s))
        except gspread.exceptions.WorksheetNotFound:
            logger.debug("Sheet '%s' not found, skipping", s)
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    _activities_cache = df
    _cache_timestamp = datetime.now()

    return df


def load_activities(start_date=None, end_date=None):
    """Load activities, optionally filtered by date range. Uses cache."""
    df = _load_all_activities().copy()

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


def _get_or_create_activities_sheet(spreadsheet):
    try:
        return spreadsheet.worksheet("Activities")
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title="Activities",
            rows=1000,
            cols=10,
        )
        ws.append_row(["Date", "Start Time", "End Time", "Activity", "User ID"],
                       value_input_option="USER_ENTERED")
        return ws


def append_activity_record(date, start_time, end_time, activity_name, user_id=None):
    """Write a general activity record to the Activities sheet."""
    spreadsheet = open_spreadsheet()
    sheet = _get_or_create_activities_sheet(spreadsheet)

    if isinstance(date, str):
        date = datetime.fromisoformat(date).date()

    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%H:%M").time()

    if isinstance(end_time, str):
        end_time = datetime.strptime(end_time, "%H:%M").time()

    start_dt = datetime.combine(date, start_time)

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
            activity_name,
            user_id or "",
        ])

    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    invalidate_activities_cache()


def get_recent_rows(n_days=14):
    """
    Returns list of dicts with raw row info for entries in the last n_days.
    Each dict: {sheet, row_num, date, start, end, label}
    row_num is 1-indexed (header is row 1, data starts at row 2).
    Sorted newest first.
    """
    spreadsheet = open_spreadsheet()
    cutoff = (datetime.now() - timedelta(days=n_days)).date()
    entries = []

    sheet_configs = [
        ("Activities", True),
        ("Sleep", False),
    ]

    for sheet_name, has_activity_col in sheet_configs:
        try:
            ws = spreadsheet.worksheet(sheet_name)
            values = ws.get_all_values()
        except Exception:
            continue

        if not values:
            continue

        for i, row in enumerate(values[1:], start=2):  # header is row 1
            date_str = row[0].strip() if row else ""
            if not date_str:
                continue
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue

            if d < cutoff:
                continue

            start_str = row[1][:5] if len(row) > 1 else ""
            end_str = row[2][:5] if len(row) > 2 else ""

            if has_activity_col:
                activity = row[3].strip() if len(row) > 3 else "?"
                label = f"{date_str} {start_str}-{end_str} {activity}"
            else:
                label = f"{date_str} {start_str}-{end_str} Sleep"

            entries.append({
                "sheet": sheet_name,
                "row_num": i,
                "date": date_str,
                "start": start_str,
                "label": label,
            })

    entries.sort(key=lambda e: (e["date"], e["start"]), reverse=True)
    return entries


def delete_sheet_row(sheet_name, row_num):
    """Delete a specific row from the given sheet. row_num is 1-indexed."""
    spreadsheet = open_spreadsheet()
    ws = spreadsheet.worksheet(sheet_name)
    ws.delete_rows(row_num)
    invalidate_activities_cache()
    logger.debug("Deleted row %d from sheet '%s'", row_num, sheet_name)


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

    # Invalidate cache so next preview shows new data
    invalidate_activities_cache()
