"""list_logs: which files are under a path, and what format each one is."""

from __future__ import annotations

import os
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from ..logs import reader
from ..logs.formats import UNKNOWN_FORMAT
from ..paths import LogRoot
from ..models import ListLogsResult, LogFile

DESCRIPTION = (
    "List the log files under a path in the log root, each with its size, whether it is gzip "
    "and its detected format. Use it first to see what exists. Results come in pages; "
    "the note says how to get the next one."
)


def listed_format(full: str) -> str:
    """The detected format; a `.gz` file that fails within the lines detection reads is listed as unknown."""
    try:
        return reader.format_of(full)
    except reader.Unreadable:
        return UNKNOWN_FORMAT


def register(mcp: FastMCP, root: LogRoot) -> None:
    def list_logs(
        path: Annotated[str, Field(max_length=500, description="File or folder, relative to the log root.")] = ".",
        limit: Annotated[int, Field(ge=1, le=500, description="Most files to return.")] = 50,
        offset: Annotated[int, Field(ge=0, description="Files to skip, for the next page.")] = 0,
    ) -> ListLogsResult:
        location = root.resolve(path)
        everything = [entry.full for entry in reader.walk(location) if not entry.symlink]
        page = [
            LogFile(
                path=root.relative(full),
                size_bytes=os.path.getsize(full),
                compressed=reader.is_compressed(full),
                format=listed_format(full),
            )
            for full in everything[offset:offset + limit]
        ]
        total, shown = len(everything), len(page)
        note = ""
        if offset + shown < total:
            note = f"Showing {shown} of {total} files. Pass offset={offset + shown} for more."
        return ListLogsResult(
            path=root.relative(location), files=page, total=total, shown=shown, note=note,
        )

    mcp.tool(
        list_logs,
        title="List log files",
        description=DESCRIPTION,
        annotations={"title": "List log files", "readOnlyHint": True, "openWorldHint": False},
    )
