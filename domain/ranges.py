from datetime import date, timedelta


def last_n_days(n: int):
    end = date.today()
    start = end - timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()


def last_month():
    end = date.today()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()


def today():
    d = date.today()
    return d.isoformat(), d.isoformat()


def yesterday():
    d = date.today() - timedelta(days=1)
    return d.isoformat(), d.isoformat()


def this_week():
    end = date.today()
    start = end - timedelta(days=end.weekday())  # Monday
    return start.isoformat(), end.isoformat()
