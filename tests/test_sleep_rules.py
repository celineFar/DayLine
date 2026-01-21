from datetime import datetime
from infra.activity_repo import _split_sleep_across_midnight


def test_sleep_crossing_midnight():
    start = datetime(2025, 1, 1, 23, 30)
    end = datetime(2025, 1, 2, 7, 0)

    segments = _split_sleep_across_midnight(start, end)

    assert len(segments) == 2
    assert segments[0][0].isoformat() == "2025-01-01"
    assert segments[1][0].isoformat() == "2025-01-02"
