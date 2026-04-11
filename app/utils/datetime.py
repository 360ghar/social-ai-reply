from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def invitation_expiry() -> datetime:
    return utc_now() + timedelta(days=7)
