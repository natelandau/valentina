"""Helper functions for Valentina."""
from datetime import datetime, timezone


def time_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0)
