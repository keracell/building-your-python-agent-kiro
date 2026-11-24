"""summarize_logs: counts and message groups for a file or folder in a window."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ..logs import reader
from ..logs.formats import LEVELS, UNKNOWN_FORMAT
from ..logs.groups import group_id, pattern_of
from ..logs.times import format_time, in_window, parse_instant
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


def parse_bound(name: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    moment = parse_instant(value)
    if moment is None:
        raise ToolError(f"{name} {value!r} is not a time: use YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS][Z|+HH:MM]")
    return moment


def show(moment: datetime | None) -> str | None:
    return None if moment is None else format_time(moment)


def register(mcp: FastMCP, root: str) -> None:
    def summarize_logs(
        path: Annotated[str, Field(max_length=500, description="File or folder, relative to the log root.")] = ".",
        since: Annotated[str | None, Field(max_length=40, description="Window start, inclusive, UTC unless it has an offset.")] = None,
        until: Annotated[str | None, Field(max_length=40, description="Window end, exclusive.")] = None,
        min_level: Annotated[MinLevel, Field(description="Lowest level whose groups are listed.")] = "warning",
        limit: Annotated[int, Field(ge=1, le=100, description="Most groups to return.")] = 20,
    ) -> SummarizeResult:
        try:
            location = reader.resolve_path(root, path)
        except reader.PathRefused as exc:
            raise ToolError(str(exc)) from None
        if not os.path.exists(location):
            raise ToolError(f"path {path!r} does not exist under the log root")
        start, end = parse_bound("since", since), parse_bound("until", until)
        floor = 0 if min_level == "any" else LEVELS.index(min_level)

        files_scanned = lines_scanned = lines_in_window = 0
        skipped: list[SkippedFile] = []
        first_seen = last_seen = None
        by_level = {level: 0 for level in LEVELS}
        groups: dict[tuple[str, str, str], _Group] = {}

        for full in reader.walk_files(location):
            relative = reader.relative_path(root, full)
            format_name = reader.format_of(full)
            if format_name == UNKNOWN_FORMAT:
                if len(skipped) < MAX_SKIPPED:
                    skipped.append(SkippedFile(path=relative, reason="unknown format"))
                continue
            files_scanned += 1
            for line in reader.read_lines(full, format_name):
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
                group.files.add(relative)
                if line.time is not None:
                    group.first_seen = line.time if group.first_seen is None else min(group.first_seen, line.time)
                    group.last_seen = line.time if group.last_seen is None else max(group.last_seen, line.time)

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
        return SummarizeResult(
            path=reader.relative_path(root, location),
            since=show(start), until=show(end), min_level=min_level,
            files_scanned=files_scanned, skipped=skipped,
            lines_scanned=lines_scanned, lines_in_window=lines_in_window,
            first_seen=show(first_seen), last_seen=show(last_seen),
            by_level=ByLevel(**by_level),
            groups=page, total_groups=total, shown=len(page), note=note,
        )

    mcp.tool(
        summarize_logs,
        title="Summarize logs",
        description=DESCRIPTION,
        annotations={"title": "Summarize logs", "readOnlyHint": True, "openWorldHint": False},
    )
