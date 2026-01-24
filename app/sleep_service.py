from __future__ import annotations

from datetime import datetime, timedelta

from infra.activity_repo import append_sleep_record

# Validation constants
MAX_SLEEP_DURATION_HOURS = 24
MIN_SLEEP_DURATION_MINUTES = 5


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

    Raises:
        ValueError: If the sleep session is invalid (negative duration,
                    too long, or too short).
    """
    if end_dt <= start_dt:
        raise ValueError("Wake time must be after sleep start time.")

    duration = end_dt - start_dt

    if duration < timedelta(minutes=MIN_SLEEP_DURATION_MINUTES):
        raise ValueError(
            f"Sleep duration must be at least {MIN_SLEEP_DURATION_MINUTES} minutes."
        )

    if duration > timedelta(hours=MAX_SLEEP_DURATION_HOURS):
        raise ValueError(
            f"Sleep duration cannot exceed {MAX_SLEEP_DURATION_HOURS} hours."
        )

    # Persist using the repo function that splits midnight
    append_sleep_record(
        date=start_dt.date().isoformat(),
        start_time=start_dt.strftime("%H:%M"),
        end_time=end_dt.strftime("%H:%M"),
        user_id=str(user_id),
    )
