from datetime import UTC, datetime


def as_utc(value: datetime) -> datetime:
    """SQLite hands back times without a timezone. Horkos always stores UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value
