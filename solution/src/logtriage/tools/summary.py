"""summarize_logs: counts and message groups for a file or folder in a window."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .. import errors
from ..logs import reader
from .. import errors
from ..logs.formats import LEVELS
from .. import errors
from ..logs.groups import group_id, pattern_of
from .. import errors
from ..logs.times import format_time, in_window, parse_instant
from ..paths import LogRoot
from ..scans import LOCAL_CALLER, MAX_LINES_PER_GROUP, ScanStore, ScannedFile, StoredGroup
from ..models import ByLevel, Example, Group, MinLevel, SkippedFile, SummarizeResult

DESCRIPTION = (
    "Count the lines of a file or folder in a time window and group them by message pattern, "
    "worst and most frequent first. Use it to see what went wrong without reading every line; "
    "then search_logs for the lines themselves."
)

MAX_SKIPPED = 20
MAX_FILES_PER_GROUP = 5
MAX_TEXT = 500


@dataclass
class _Group:
    format: str
    level: str
    pattern: str
    count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    files: set[str] = field(default_factory=set)
    example: Example | None = None
    positions: list[tuple[str, int]] = field(default_factory=list)


def parse_bound(name: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    moment = parse_instant(value)
    if moment is None:
        raise ToolError(errors.bad_time(name))
    return moment


def parse_window(since: str | None, until: str | None) -> tuple[datetime | None, datetime | None]:
    """The window ends, or E3 (since is reported first) and E4 when until is not later than since."""
    start, end = parse_bound("since", since), parse_bound("until", until)
    if start is not None and end is not None and end <= start:
        raise ToolError(errors.UNTIL_NOT_LATER)
    return start, end


def show(moment: datetime | None) -> str | None:
    return None if moment is None else format_time(moment)


def register(mcp: FastMCP, root: LogRoot, store: ScanStore) -> None:
    def summarize_logs(
        path: Annotated[str, Field(max_length=500, description="File or folder, relative to the log root.")] = ".",
        since: Annotated[str | None, Field(max_length=40, description="Window start, inclusive, UTC unless it has an offset.")] = None,
        until: Annotated[str | None, Field(max_length=40, description="Window end, exclusive.")] = None,
        min_level: Annotated[MinLevel, Field(description="Lowest level whose groups are listed.")] = "warning",
        limit: Annotated[int, Field(ge=1, le=100, description="Most groups to return.")] = 20,
    ) -> SummarizeResult:
        location = root.resolve(path)
        start, end = parse_window(since, until)
        floor = 0 if min_level == "any" else LEVELS.index(min_level)

        files_scanned = lines_scanned = lines_in_window = 0
        skipped: list[SkippedFile] = []
        first_seen = last_seen = None
        by_level = {level: 0 for level in LEVELS}
        groups: dict[tuple[str, str, str], _Group] = {}
        scanned: dict[str, ScannedFile] = {}

        for entry in reader.walk(location):
            relative = root.relative(entry.full)
            try:
                format_name, file_lines = reader.load_for_scan(entry)
            except reader.Skipped as skip:
                skipped.append(SkippedFile(path=relative, reason=skip.reason))
                continue
            files_scanned += 1
            scanned[relative] = ScannedFile(format_name)
            for line in file_lines:
                lines_scanned += 1
                if not in_window(line.time, start, end):
                    continue
                lines_in_window += 1
                by_level[line.level] += 1
                if line.time is not None:
                    first_seen = line.time if first_seen is None else min(first_seen, line.time)
                    last_seen = line.time if last_seen is None else max(last_seen, line.time)
                if LEVELS.index(line.level) < floor:
                    continue
                key = (format_name, line.level, pattern_of(line.message))
                group = groups.get(key)
                if group is None:
                    group = groups[key] = _Group(format_name, line.level, key[2])
                    group.example = Example(file=relative, line=line.number, text=line.text[:MAX_TEXT])
                group.count += 1
                if len(group.positions) < MAX_LINES_PER_GROUP:
                    group.positions.append((relative, line.number))
                group.files.add(relative)
                if line.time is not None:
                    group.first_seen = line.time if group.first_seen is None else min(group.first_seen, line.time)
                    group.last_seen = line.time if group.last_seen is None else max(group.last_seen, line.time)

        skipped = sorted(skipped, key=lambda item: os.fsencode(item.path))[:MAX_SKIPPED]

        ordered = sorted(
            ((group_id(g.format, g.level, g.pattern), g) for g in groups.values()),
            key=lambda item: (
                -item[1].count,
                item[1].first_seen is None,
                item[1].first_seen.timestamp() if item[1].first_seen else 0.0,
                item[0],
            ),
        )
        total = len(ordered)
        page = [
            Group(
                group_id=gid, format=g.format, level=g.level, pattern=g.pattern, count=g.count,
                first_seen=show(g.first_seen), last_seen=show(g.last_seen),
                file_count=len(g.files),
                files=sorted(g.files, key=os.fsencode)[:MAX_FILES_PER_GROUP],
                example=g.example,
            )
            for gid, g in ordered[:limit]
        ]
        note = ""
        if len(page) < total:
            note = (
                f"Showing {len(page)} of {total} groups. "
                "Raise limit (up to 100) or narrow the path or the window."
            )
        expires_at = datetime.now(UTC) + timedelta(seconds=store.ttl_seconds)
        result = SummarizeResult(
            scan_id=store.new_id(), expires_at=format_time(expires_at),
            path=root.relative(location),
            since=show(start), until=show(end), min_level=min_level,
            files_scanned=files_scanned, skipped=skipped,
            lines_scanned=lines_scanned, lines_in_window=lines_in_window,
            first_seen=show(first_seen), last_seen=show(last_seen),
            by_level=ByLevel(**by_level),
            groups=page, total_groups=total, shown=len(page), note=note,
        )
        request = {"path": result.path, "since": result.since, "until": result.until, "min_level": min_level}
        kept = {gid: StoredGroup(g.pattern, g.count, g.positions) for gid, g in ordered}
        store.add(LOCAL_CALLER, result.scan_id, request, result, scanned, kept)
        return result

    mcp.tool(
        summarize_logs,
        title="Summarize logs",
        description=DESCRIPTION,
        annotations={"title": "Summarize logs", "readOnlyHint": True, "openWorldHint": False},
    )
