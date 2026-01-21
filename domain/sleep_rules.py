# domain/sleep_rules.py

import pandas as pd
from config.settings import DAY_MINUTES, MAX_SLEEP_START
from domain.time_normalize import add_minute_columns


def add_sleep_intervals(df):
    df = add_minute_columns(df)
    rows = []

    for date, day in df.groupby("Date"):
        rows.append(day)

        if (day["source"] == "Sleep").any():
            continue

        intervals = day[["start_min", "end_min"]].dropna()

        sleep_start = 0
        sleep_end = 8 * 60

        overlaps = (
            (intervals["start_min"] < sleep_end)
            & (intervals["end_min"] > sleep_start)
        ).any()

        if overlaps:
            early = intervals[intervals["end_min"] <= MAX_SLEEP_START]
            if early.empty:
                continue

            last_end = early["end_min"].max()
            sleep_start = last_end + 60
            sleep_end = sleep_start + 8 * 60

            if sleep_start > MAX_SLEEP_START:
                continue

        sleep_end = min(sleep_end, DAY_MINUTES)

        rows.append(
            pd.DataFrame([{
                "Date": date,
                "source": "Sleep",
                "start_min": sleep_start,
                "end_min": sleep_end,
            }])
        )

    return pd.concat(rows, ignore_index=True)
