"""save_finding: write one finding as a markdown file under the reports folder."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware
from pydantic import BaseModel, ConfigDict, Field

from .. import errors
from ..auth import caller_is_read_only
from ..logs import reader
from ..logs.times import UTC, format_time
from ..models import SaveFindingResult, Severity
from ..paths import LogRoot

DESCRIPTION = (
    "Save a finding as a markdown report with its severity, summary and the log lines that prove "
    "it. Cite a file and line for every piece of evidence. It only creates: a title whose name is "
    "already taken is refused and the earlier report stays unchanged."
)

MAX_SLUG = 60


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: Annotated[str, Field(max_length=500, description="Log file, relative to the log root.")]
    line: Annotated[int, Field(ge=1, description="Line number in that file, from 1.")]
    note: Annotated[str, Field(min_length=1, max_length=300, description="What this line shows.")]


def slugify(title: str) -> str:
    """The report's name: ASCII letters lowered, runs of anything else one `-`, cut to 60, never empty."""
    lowered = title.translate({code: code + 32 for code in range(ord("A"), ord("Z") + 1)})
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = slug[:MAX_SLUG].rstrip("-")
    return slug or "finding"


def render(title: str, severity: str, saved: str, summary: str, evidence: list[EvidenceItem]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Severity: {severity}",
        f"- Saved: {saved}",
        "",
        summary,
        "",
        "## Evidence",
        "",
        *(f"- `{item.file}` line {item.line}: {item.note}" for item in evidence),
    ]
    return "\n".join(lines) + "\n"


def check_evidence(root: LogRoot, item: EvidenceItem) -> None:
    """The file is screened like a path (E1, E2), must be a file (E10), and must have the line (E8)."""
    location = root.resolve(item.file)
    name = root.relative(location)
    if os.path.isdir(location):
        raise ToolError(errors.is_a_folder(name))
    total = sum(1 for _ in reader.iter_lines(location))
    if item.line > total:
        raise ToolError(errors.line_past_end(item.line, name, total))


class FindingAccessMiddleware(Middleware):
    """Hide the write tool and refuse direct writes by read-only callers."""

    async def on_list_tools(self, context, call_next):
        tools = await call_next(context)
        if caller_is_read_only():
            return [tool for tool in tools if tool.name != "save_finding"]
        return tools

    async def on_call_tool(self, context, call_next):
        if context.message.name == "save_finding" and caller_is_read_only():
            raise ToolError(errors.FINDING_NOT_AVAILABLE)
        return await call_next(context)


def register(mcp: FastMCP, reports: str, root: LogRoot) -> None:
    mcp.add_middleware(FindingAccessMiddleware())

    def save_finding(
        title: Annotated[str, Field(min_length=3, max_length=120, description="Short name of the finding.")],
        severity: Annotated[Severity, Field(description="How serious the finding is.")],
        summary: Annotated[str, Field(min_length=1, max_length=4000, description="What happened and why.")],
        evidence: Annotated[list[EvidenceItem], Field(min_length=1, max_length=20, description="The log lines that prove it.")],
    ) -> SaveFindingResult:
        name = slugify(title)
        saved = format_time(datetime.now(UTC))
        filename = f"{name}.md"
        target = os.path.join(reports, filename)
        if os.path.lexists(target):
            raise ToolError(errors.finding_exists(name))
        for item in evidence:
            check_evidence(root, item)
        os.makedirs(reports, exist_ok=True)
        try:
            with open(target, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(render(title, severity, saved, summary, evidence))
        except FileExistsError:
            raise ToolError(errors.finding_exists(name)) from None
        return SaveFindingResult(name=name, path=filename, created=saved)

    mcp.tool(
        save_finding,
        title="Save a finding",
        description=DESCRIPTION,
        annotations={
            "title": "Save a finding",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
