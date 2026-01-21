# domain/time_normalize.py

import pandas as pd


def add_minute_columns(df):
    df = df.copy()

    df["Start Time"] = pd.to_datetime(df["Start Time"], format="%H:%M:%S")
    df["End Time"] = pd.to_datetime(df["End Time"], format="%H:%M:%S")

    df["start_min"] = (
        df["Start Time"].dt.hour * 60
        + df["Start Time"].dt.minute
        + df["Start Time"].dt.second / 60
    )

    df["end_min"] = (
        df["End Time"].dt.hour * 60
        + df["End Time"].dt.minute
        + df["End Time"].dt.second / 60
    )

    return df
