"""group_lines: the lines of one group of a stored scan, paged, without scanning again."""

from __future__ import annotations

import os
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .. import errors
from ..logs import reader
from ..logs.times import format_time
from ..models import GroupLine, GroupLinesResult, NumberedLine, ReadLinesResult
from ..paths import LogRoot
from ..auth import current_caller
from ..scans import MAX_LINES_PER_GROUP, ScanStore

DESCRIPTION = (
    "Page through the lines of one message group from a summarize_logs scan, using its scan_id and "
    "a group_id from that scan, without scanning the logs again."
)

READ_DESCRIPTION = (
    "Read the lines around one line of one file under the log root, for context: a few lines before "
    "and after it, clipped to the start and the end of the file."
)

MAX_TEXT = 500


def register(mcp: FastMCP, root: LogRoot, store: ScanStore) -> None:
    def group_lines(
        scan_id: Annotated[str, Field(pattern=r"^s_[0-9a-f]{16}$", description="The scan_id from summarize_logs.")],
        group_id: Annotated[str, Field(pattern=r"^[0-9a-f]{12}$", description="A group_id from that scan's groups.")],
        limit: Annotated[int, Field(ge=1, le=200, description="Most lines to return.")] = 50,
        offset: Annotated[int, Field(ge=0, description="Lines to skip, for the next page.")] = 0,
    ) -> GroupLinesResult:
        scan = store.get(current_caller(), scan_id)
        if scan is None:
            raise ToolError(errors.scan_unknown(scan_id))
        group = scan.groups.get(group_id)
        if group is None:
            raise ToolError(errors.group_not_in_scan(group_id, scan_id))

        kept = len(group.positions)
        page = group.positions[offset:offset + limit]
        wanted: dict[str, set[int]] = {}
        for relative, number in page:
            wanted.setdefault(relative, set()).add(number)
        found: dict[tuple[str, int], reader.Line] = {}
        for relative, numbers in wanted.items():
            scanned = scan.files[relative]
            location = root.resolve(relative)  # screened again: the file or a parent may have been replaced
            for line in reader.read_lines(location, scanned.format):
                if line.number in numbers:
                    found[(relative, line.number)] = line
        lines = [
            GroupLine(
                file=relative, line=number,
                time=None if found[(relative, number)].time is None else format_time(found[(relative, number)].time),
                text=found[(relative, number)].text[:MAX_TEXT],
            )
            for relative, number in page
        ]

        shown = len(lines)
        note = ""
        if offset + shown < kept:
            note = f"Showing {shown} of {group.count} lines. Pass offset={offset + shown} for more."
        if group.count > MAX_LINES_PER_GROUP:
            tail = f"Only the first {MAX_LINES_PER_GROUP} lines are kept."
            note = f"{note} {tail}" if note else tail
        return GroupLinesResult(
            scan_id=scan_id, group_id=group_id, pattern=group.pattern,
            lines=lines, total=group.count, shown=shown, note=note,
        )

    mcp.tool(
        group_lines,
        title="Show a group's lines",
        description=DESCRIPTION,
        annotations={"title": "Show a group's lines", "readOnlyHint": True, "openWorldHint": False},
    )

    def read_lines(
        path: Annotated[str, Field(max_length=500, description="A file, relative to the log root.")],
        line: Annotated[int, Field(ge=1, description="The line to read around, counted from 1.")],
        before: Annotated[int, Field(ge=0, le=50, description="Lines to show before it.")] = 5,
        after: Annotated[int, Field(ge=0, le=200, description="Lines to show after it.")] = 20,
    ) -> ReadLinesResult:
        location = root.resolve(path)
        name = root.relative(location)
        if os.path.isdir(location):
            raise ToolError(errors.is_a_folder(name))

        start, end = max(1, line - before), line + after
        window: list[NumberedLine] = []
        total = 0
        for total, text in enumerate(reader.iter_lines(location), start=1):
            if start <= total <= end:
                window.append(NumberedLine(line=total, text=text[:MAX_TEXT]))
        if line > total:
            raise ToolError(errors.line_past_end(line, name, total))
        return ReadLinesResult(
            file=name, start=start, end=min(end, total), total_lines=total, lines=window,
        )

    mcp.tool(
        read_lines,
        title="Read lines around a line",
        description=READ_DESCRIPTION,
        annotations={"title": "Read lines around a line", "readOnlyHint": True, "openWorldHint": False},
    )
