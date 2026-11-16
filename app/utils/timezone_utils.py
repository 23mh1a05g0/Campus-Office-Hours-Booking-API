"""Timezone and date conversion utilities using Python standard library zoneinfo."""
from datetime import datetime, timezone
import re
import zoneinfo
from app.exceptions.booking_exceptions import (
    InvalidTimezoneError,
    NonexistentLocalTimeError,
)

# Regex to validate naive ISO-8601 local datetime strings without offsets or Z
LOCAL_DATETIME_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$"
)

UTC_TZ = timezone.utc


def validate_iana_timezone(tz_name: str) -> zoneinfo.ZoneInfo:
    """Validate and return ZoneInfo for an IANA timezone identifier.

    Raises:
        InvalidTimezoneError: If timezone identifier is invalid or unknown.
    """
    if not tz_name or not isinstance(tz_name, str):
        raise InvalidTimezoneError(str(tz_name))

    clean_tz = tz_name.strip()
    try:
        return zoneinfo.ZoneInfo(clean_tz)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, KeyError):
        raise InvalidTimezoneError(clean_tz)


def parse_and_validate_local_datetime(date_str: str) -> datetime:
    """Parse naive local ISO datetime string and reject strings containing offsets or 'Z'.

    Raises:
        ValueError: If format is invalid or contains timezone information.
    """
    if not isinstance(date_str, str):
        raise ValueError("local_start_time must be a string in ISO-8601 format.")

    date_str_clean = date_str.strip()

    # Reject any presence of timezone indicators
    if date_str_clean.endswith("Z") or date_str_clean.endswith("z"):
        raise ValueError("local_start_time must not contain a UTC offset or Z suffix.")
    if "+" in date_str_clean:
        raise ValueError("local_start_time must not contain a UTC offset or Z suffix.")
    # Detect negative offset in time part (e.g. 10:00:00-05:00)
    time_part = date_str_clean.split("T")[-1] if "T" in date_str_clean else ""
    if "-" in time_part:
        raise ValueError("local_start_time must not contain a UTC offset or Z suffix.")

    if not LOCAL_DATETIME_REGEX.match(date_str_clean):
        raise ValueError(
            f"Invalid local datetime format '{date_str}'. Expected format: YYYY-MM-DDTHH:MM:SS"
        )

    try:
        parsed = datetime.fromisoformat(date_str_clean)
    except ValueError as e:
        raise ValueError(f"Invalid local datetime value: {e}")

    # Ensure it is naive
    if parsed.tzinfo is not None:
        raise ValueError("local_start_time must not contain a UTC offset or Z suffix.")

    return parsed


def local_to_utc(local_dt: datetime, tz_name: str) -> tuple[datetime, datetime]:
    """Convert naive local datetime into aware local datetime and normalized UTC instant.

    Handles:
      1. Nonexistent local times during DST Spring Forward (raises NonexistentLocalTimeError).
      2. Ambiguous local times during DST Fall Back (selects fold=0, the earlier occurrence).

    Returns:
        tuple[datetime, datetime]: (aware_local_datetime_with_fold0, aware_utc_datetime)
    """
    tz = validate_iana_timezone(tz_name)

    # In Python zoneinfo (PEP 495), check both fold=0 and fold=1
    dt_fold0 = local_dt.replace(tzinfo=tz, fold=0)
    dt_fold1 = local_dt.replace(tzinfo=tz, fold=1)

    # Convert both to UTC and back to verify if the wall clock time exists in local timezone
    fold0_roundtrip = dt_fold0.astimezone(UTC_TZ).astimezone(tz).replace(tzinfo=None)
    fold1_roundtrip = dt_fold1.astimezone(UTC_TZ).astimezone(tz).replace(tzinfo=None)

    # If neither fold roundtrips to the wall-clock time, it is a nonexistent time (DST gap)
    if fold0_roundtrip != local_dt and fold1_roundtrip != local_dt:
        raise NonexistentLocalTimeError(
            "Invalid local time: this time does not exist due to a daylight saving time transition."
        )

    # For ambiguous times (DST Fall Back), select fold=0 (earlier occurrence)
    chosen_local = dt_fold0
    utc_instant = chosen_local.astimezone(UTC_TZ)

    return chosen_local, utc_instant


def utc_to_local_iso(utc_dt: datetime, original_tz_name: str) -> str:
    """Convert a UTC instant to original IANA timezone and format as ISO-8601 with offset.

    Example:
        2024-10-15T10:00:00-05:00
    """
    tz = validate_iana_timezone(original_tz_name)

    # Ensure utc_dt is timezone-aware in UTC
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=UTC_TZ)
    else:
        utc_dt = utc_dt.astimezone(UTC_TZ)

    local_dt = utc_dt.astimezone(tz)
    return local_dt.isoformat()
