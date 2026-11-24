"""timeline: how often something happened over time, and how a number in those lines moved."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .. import errors
from ..logs import reader
from ..logs.times import format_time, in_window, parse_instant
from ..models import TimelineBucket, TimelineResult
from ..paths import LogRoot
from ..scans import LOCAL_CALLER, ScanStore

DESCRIPTION = (
    "Count the lines of a scan's files by time bucket, optionally only those matching a pattern, and "
    "summarize a number captured from them (min, median, max). Use it to see how something changed over time."
)

MAX_BUCKETS = 500
NUMBER = re.compile(r"[+-]?\d+(\.\d+)?", re.ASCII)


def compile_pattern(field: str, text: str | None) -> re.Pattern[str] | None:
    if text is None:
        return None
    try:
        return re.compile(text, re.ASCII)
    except re.error:
        raise ToolError(errors.bad_pattern(field)) from None


def midnight(moment: datetime) -> datetime:
    return moment.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def value_of(expression: re.Pattern[str], text: str) -> float | None:
    """The first match's group as a number, or None: no match, text that is not a plain decimal, or a number
    too large for a finite float. The line is counted either way."""
    match = expression.search(text)
    if not match:
        return None
    group = match.group(1)
    if group is None or not NUMBER.fullmatch(group):
        return None
    number = float(group)
    return number if math.isfinite(number) else None


def median_of(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    result = ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2
    return round(result, 3)


def register(mcp: FastMCP, root: LogRoot, store: ScanStore) -> None:
    def timeline(
        scan_id: Annotated[str, Field(pattern=r"^s_[0-9a-f]{16}$", description="The scan_id from summarize_logs.")],
        pattern: Annotated[str | None, Field(min_length=1, max_length=200, description="Count only lines this regular expression matches; none counts every line in the window.")] = None,
        bucket_minutes: Annotated[int, Field(ge=1, le=1440, description="Width of a bucket in minutes.")] = 60,
        value_pattern: Annotated[str | None, Field(min_length=1, max_length=200, description="A regular expression with exactly one capture group, for a number in the lines.")] = None,
    ) -> TimelineResult:
        scan = store.get(LOCAL_CALLER, scan_id)
        if scan is None:
            raise ToolError(errors.scan_unknown(scan_id))
        expression = compile_pattern("pattern", pattern)
        value_expression = compile_pattern("value_pattern", value_pattern)
        if value_expression is not None and value_expression.groups != 1:
            raise ToolError(errors.one_capture_group("value_pattern"))

        since = parse_instant(scan.request["since"]) if scan.request["since"] else None
        until = parse_instant(scan.request["until"]) if scan.request["until"] else None
        width = bucket_minutes * 60

        def grid_start(anchor: datetime, moment: datetime) -> datetime:
            return anchor + timedelta(seconds=((moment - anchor).total_seconds() // width) * width)

        first_bucket = None
        if since is not None:
            anchor = midnight(since)
            first_bucket = grid_start(anchor, since)
            if until is not None:
                needed = math.ceil((until - first_bucket).total_seconds() / width)
                if needed > MAX_BUCKETS:
                    raise ToolError(errors.too_many_buckets(needed))

        counted: list[tuple[datetime, float | None]] = []
        for relative, scanned in scan.files.items():
            location = root.resolve(relative)  # screened again before it is opened
            for line in reader.read_lines(location, scanned.format):
                if line.time is None or not in_window(line.time, since, until):
                    continue
                if expression is not None and not expression.search(line.text):
                    continue
                value = value_of(value_expression, line.text) if value_expression is not None else None
                counted.append((line.time, value))

        if since is None:
            anchor = midnight(min(t for t, _ in counted)) if counted else None
            first_bucket = grid_start(anchor, min(t for t, _ in counted)) if counted else None
        last_bucket = None
        if until is not None and first_bucket is not None:
            needed = math.ceil((until - first_bucket).total_seconds() / width)
            last_bucket = first_bucket + timedelta(seconds=(needed - 1) * width) if needed >= 1 else None
        elif counted and first_bucket is not None:
            last_bucket = grid_start(anchor, max(t for t, _ in counted))

        buckets: list[TimelineBucket] = []
        end = None
        if first_bucket is not None and last_bucket is not None:
            needed = int((last_bucket - first_bucket).total_seconds() // width) + 1
            if needed > MAX_BUCKETS:
                raise ToolError(errors.too_many_buckets(needed))
            tallies: list[list[float | None]] = [[] for _ in range(needed)]
            counts = [0] * needed
            for moment, value in counted:
                index = int((grid_start(anchor, moment) - first_bucket).total_seconds() // width)
                counts[index] += 1
                if value is not None:
                    tallies[index].append(value)
            for index in range(needed):
                values = tallies[index]
                buckets.append(TimelineBucket(
                    start=format_time(first_bucket + timedelta(seconds=index * width)),
                    count=counts[index], value_count=len(values),
                    min=min(values) if values else None,
                    median=median_of(values) if values else None,
                    max=max(values) if values else None,
                ))
            end = format_time(last_bucket + timedelta(seconds=width))
        return TimelineResult(
            scan_id=scan_id, pattern=pattern, value_pattern=value_pattern, bucket_minutes=bucket_minutes,
            start=None if first_bucket is None else format_time(first_bucket), end=end,
            total=len(counted), buckets=buckets,
        )

    mcp.tool(
        timeline,
        title="Timeline of matching lines",
        description=DESCRIPTION,
        annotations={"title": "Timeline of matching lines", "readOnlyHint": True, "openWorldHint": False},
    )
