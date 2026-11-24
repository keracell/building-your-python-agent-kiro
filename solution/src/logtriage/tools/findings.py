"""save_finding: write one finding as a markdown file under the reports folder."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Annotated

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..logs.times import UTC, format_time
from ..models import SaveFindingResult, Severity

DESCRIPTION = (
    "Save a finding as a markdown report with its severity, summary and the log lines that prove "
    "it. Cite a file and line for every piece of evidence. Saving a title that already exists "
    "overwrites the earlier report."
)

MAX_SLUG = 60


class EvidenceItem(BaseModel):
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


def register(mcp: FastMCP, reports: str) -> None:
    def save_finding(
        title: Annotated[str, Field(min_length=3, max_length=120, description="Short name of the finding.")],
        severity: Annotated[Severity, Field(description="How serious the finding is.")],
        summary: Annotated[str, Field(min_length=1, max_length=4000, description="What happened and why.")],
        evidence: Annotated[list[EvidenceItem], Field(min_length=1, max_length=20, description="The log lines that prove it.")],
    ) -> SaveFindingResult:
        name = slugify(title)
        saved = format_time(datetime.now(UTC))
        os.makedirs(reports, exist_ok=True)
        filename = f"{name}.md"
        with open(os.path.join(reports, filename), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render(title, severity, saved, summary, evidence))
        return SaveFindingResult(name=name, path=filename, created=saved)

    mcp.tool(
        save_finding,
        title="Save a finding",
        description=DESCRIPTION,
        annotations={
            "title": "Save a finding",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    )
