from datetime import datetime, timedelta, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def invitation_expiry() -> datetime:
    return utc_now() + timedelta(days=7)
