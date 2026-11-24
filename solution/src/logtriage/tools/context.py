"""group_lines: the lines of one group of a stored scan, paged, without scanning again."""

from __future__ import annotations

from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .. import errors
from ..logs import reader
from ..logs.times import format_time
from ..models import GroupLine, GroupLinesResult
from ..scans import LOCAL_CALLER, MAX_LINES_PER_GROUP, ScanStore

DESCRIPTION = (
    "Page through the lines of one message group from a summarize_logs scan, using its scan_id and "
    "a group_id from that scan, without scanning the logs again."
)

MAX_TEXT = 500


def register(mcp: FastMCP, store: ScanStore) -> None:
    def group_lines(
        scan_id: Annotated[str, Field(pattern=r"^s_[0-9a-f]{16}$", description="The scan_id from summarize_logs.")],
        group_id: Annotated[str, Field(pattern=r"^[0-9a-f]{12}$", description="A group_id from that scan's groups.")],
        limit: Annotated[int, Field(ge=1, le=200, description="Most lines to return.")] = 50,
        offset: Annotated[int, Field(ge=0, description="Lines to skip, for the next page.")] = 0,
    ) -> GroupLinesResult:
        scan = store.get(LOCAL_CALLER, scan_id)
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
            for line in reader.read_lines(scanned.full, scanned.format):
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
