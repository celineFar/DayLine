# domain/timeline.py

import pandas as pd
from domain.sleep_rules import add_sleep_intervals


def build_wide_intervals(df):
    df = add_sleep_intervals(df)
    df = df.sort_values(["Date", "start_min"])
    df["interval"] = df.groupby("Date").cumcount() + 1

    wide = df.pivot(
        index="Date",
        columns="interval",
        values=["start_min", "end_min", "source"],
    )

    ordered = []
    max_i = wide.columns.get_level_values(1).max()

    for i in range(1, max_i + 1):
        for field in ("start_min", "end_min", "source"):
            if (field, i) in wide.columns:
                ordered.append((field, i))

    wide = wide[ordered]
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.reset_index()

    def extract_intervals(row):
        out = []
        i = 1
        while f"start_min_{i}" in row:
            s = row[f"start_min_{i}"]
            e = row[f"end_min_{i}"]
            src = row[f"source_{i}"]
            if pd.notna(s) and pd.notna(e) and e > s:
                out.append((s, e - s, src))
            i += 1
        return out

    wide["intervals"] = wide.apply(extract_intervals, axis=1)
    return wide
