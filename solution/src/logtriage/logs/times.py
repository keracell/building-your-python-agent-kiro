"""Times as docs/log-formats.md reads them: whole seconds, UTC."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

MONTHS = {
    name: number
    for number, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), start=1
    )
}

# The grammar of run headers and of the tools' since and until.
INSTANT = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})"
    r"(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(Z|[+-]\d{2}:\d{2})?)?",
    re.ASCII,
)


def build_time(
    year: int, month: int, day: int, hour: int, minute: int, second: int,
    sign: str = "+", offset_hours: int = 0, offset_minutes: int = 0,
) -> datetime | None:
    """A UTC time from fields and an optional offset, or None when the fields are not a real time."""
    if offset_hours > 23 or offset_minutes > 59:
        return None
    try:
        moment = datetime(year, month, day, hour, minute, second, tzinfo=UTC)
        shift = timedelta(hours=offset_hours, minutes=offset_minutes)
        return moment - shift if sign == "+" else moment + shift
    except (ValueError, OverflowError):
        return None


def parse_instant(text: str) -> datetime | None:
    """Read `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM[:SS[.fff]][Z|±HH:MM]`; None when it does not read that way."""
    match = INSTANT.fullmatch(text)
    if not match:
        return None
    year, month, day, hour, minute, second, zone = match.groups()
    sign, offset_hours, offset_minutes = "+", 0, 0
    if zone and zone != "Z":
        sign, offset_hours, offset_minutes = zone[0], int(zone[1:3]), int(zone[4:6])
    return build_time(
        int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0),
        sign, offset_hours, offset_minutes,
    )


def format_time(moment: datetime) -> str:
    """Output form: `YYYY-MM-DDTHH:MM:SSZ`, UTC, fractions cut."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_window(moment: datetime | None, since: datetime | None, until: datetime | None) -> bool:
    """`since <= time < until`; with neither end every line is in, with either a line without a time is out."""
    if since is None and until is None:
        return True
    if moment is None:
        return False
    return (since is None or since <= moment) and (until is None or moment < until)
