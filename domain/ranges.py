from datetime import date, timedelta


def last_n_days(n: int):
    end = date.today()
    start = end - timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()


def last_month():
    end = date.today()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()
