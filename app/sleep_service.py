from __future__ import annotations

from datetime import datetime
from typing import Optional

from infra.activity_repo import append_sleep_record


def record_sleep_start(*, user_id: int, start_dt: datetime) -> None:
    """
    Pure intent: bot decides 'now' and passes it in.
    State storage is handled by bot/state.py, not here.
    This service is responsible for writing finalized intervals.
    """
    # For quick-action flow, we don't write anything yet.
    # We only write once we also have end_dt.
    return


def record_sleep_end(
    *,
    user_id: int,
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    """
    Takes concrete datetimes and persists them as one or more Sleep rows.
    """
    if end_dt <= start_dt:
        # If user hits wake accidentally before start, treat as invalid
        raise ValueError("Wake time must be after sleep start time.")

    # Persist using the repo function that splits midnight
    append_sleep_record(
        date=start_dt.date().isoformat(),
        start_time=start_dt.strftime("%H:%M"),
        end_time=end_dt.strftime("%H:%M"),
        user_id=str(user_id),
    )
