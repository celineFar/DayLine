from __future__ import annotations

from datetime import datetime, timedelta

from infra.activity_repo import append_activity_record

MAX_ACTIVITY_DURATION_HOURS = 24
MIN_ACTIVITY_DURATION_MINUTES = 1


def record_activity(
    *,
    user_id: int,
    activity_name: str,
    start_dt: datetime,
    end_dt: datetime,
) -> None:
    if end_dt <= start_dt:
        raise ValueError("End time must be after start time.")

    duration = end_dt - start_dt

    if duration < timedelta(minutes=MIN_ACTIVITY_DURATION_MINUTES):
        raise ValueError(
            f"Activity duration must be at least {MIN_ACTIVITY_DURATION_MINUTES} minute(s)."
        )

    if duration > timedelta(hours=MAX_ACTIVITY_DURATION_HOURS):
        raise ValueError(
            f"Activity duration cannot exceed {MAX_ACTIVITY_DURATION_HOURS} hours."
        )

    append_activity_record(
        date=start_dt.date().isoformat(),
        start_time=start_dt.strftime("%H:%M"),
        end_time=end_dt.strftime("%H:%M"),
        activity_name=activity_name,
        user_id=str(user_id),
    )
