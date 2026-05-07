"""
Data general utilities
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def get_datetime_now() -> str:
    """
    Get the current datetime in ISO format with UTC timezone.
    """
    return datetime.now(tz=timezone.utc).isoformat()

def get_formatted_datetime_now(timezone_name: str = "UTC") -> str:
    """
    Get formatted datetime string for the specified timezone.

    Args:
        timezone_name (str): The name of the timezone to use in IANA timezone format. Defaults to "UTC".

    Returns:
        str: The formatted datetime string.
    """
    try:
        tz = ZoneInfo(timezone_name)
    except KeyError:
        tz = ZoneInfo("UTC")
    result = f"{datetime.now(tz).strftime('%A - %d/%m/%Y - %H:%M:%S')} ({timezone_name})"
    return result
