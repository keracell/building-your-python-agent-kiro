"""search_logs: the lines that match a regular expression."""

from __future__ import annotations

import re
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .. import errors
from ..logs import reader
from ..logs.formats import LEVELS
from ..logs.times import in_window
from ..paths import LogRoot
from ..models import MinLevel, SearchMatch, SearchResult
from .summary import parse_window, show

DESCRIPTION = (
    "Find the log lines that match a regular expression, searched anywhere in the raw line, "
    "within a path and a time window, in file and line order. Use it to read the lines behind a "
    "group from summarize_logs. Results come in pages."
)

MAX_TEXT = 500


def register(mcp: FastMCP, root: LogRoot) -> None:
    def search_logs(
        pattern: Annotated[str, Field(min_length=1, max_length=200, description="Regular expression, case-sensitive; (?i) allowed.")],
        path: Annotated[str, Field(max_length=500, description="File or folder, relative to the log root.")] = ".",
        since: Annotated[str | None, Field(max_length=40, description="Window start, inclusive, UTC unless it has an offset.")] = None,
        until: Annotated[str | None, Field(max_length=40, description="Window end, exclusive.")] = None,
        min_level: Annotated[MinLevel, Field(description="Lowest level a matching line may have.")] = "any",
        limit: Annotated[int, Field(ge=1, le=200, description="Most matches to return.")] = 50,
        offset: Annotated[int, Field(ge=0, description="Matches to skip, for the next page.")] = 0,
    ) -> SearchResult:
        location = root.resolve(path)
        start, end = parse_window(since, until)
        try:
            expression = re.compile(pattern, re.ASCII)
        except re.error:
            raise ToolError(errors.bad_pattern("pattern")) from None
        floor = 0 if min_level == "any" else LEVELS.index(min_level)

        matches: list[SearchMatch] = []
        for entry in reader.walk(location):
            try:
                _, file_lines = reader.load_for_scan(entry)
            except reader.Skipped:
                continue
            relative = root.relative(entry.full)
            for line in file_lines:
                if (
                    in_window(line.time, start, end)
                    and LEVELS.index(line.level) >= floor
                    and expression.search(line.text)
                ):
                    matches.append(
                        SearchMatch(
                            file=relative, line=line.number, time=show(line.time),
                            level=line.level, text=line.text[:MAX_TEXT],
                        )
                    )
        page = matches[offset:offset + limit]
        total, shown = len(matches), len(page)
        note = ""
        if offset + shown < total:
            note = f"Showing {shown} of {total} matches. Pass offset={offset + shown} for more."
        return SearchResult(
            path=root.relative(location), pattern=pattern,
            matches=page, total=total, shown=shown, note=note,
        )

    mcp.tool(
        search_logs,
        title="Search logs",
        description=DESCRIPTION,
        annotations={"title": "Search logs", "readOnlyHint": True, "openWorldHint": False},
    )
