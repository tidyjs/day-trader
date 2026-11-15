"""Time helpers. All scheduling logic is in America/New_York (SPEC 3)."""
from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone

from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def at_et(d: date, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return datetime.combine(d, time(h, m), tzinfo=ET)


def to_utc_z(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


_FRAC = re.compile(r"(\.\d{6})\d+")


def parse_ts(s: str) -> datetime:
    """RFC 3339 timestamp. Alpaca quotes carry nanoseconds; datetime holds
    microseconds, so fractions are cut to 6 digits."""
    return datetime.fromisoformat(_FRAC.sub(r"\1", s.replace("Z", "+00:00")))


def data_cutoff(as_of: datetime, delay_minutes: int) -> datetime:
    """Latest instant whose SIP data may be used at `as_of`.

    Rounded down to the minute so a 1-min bar is either fully before the
    cutoff or excluded. This is the no-look-ahead boundary for the scan.
    """
    c = as_of - timedelta(minutes=delay_minutes)
    return c.replace(second=0, microsecond=0)


def bar_complete_before(bar_ts: str, cutoff: datetime, minutes: int = 1) -> bool:
    """True if a bar starting at bar_ts closed at or before cutoff."""
    return parse_ts(bar_ts) + timedelta(minutes=minutes) <= cutoff
