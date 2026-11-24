"""Output models of the tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

LogFormat = Literal[
    "app", "nginx-access", "nginx-error", "php-fpm", "postgres", "redis", "syslog", "pytest", "gotest", "unknown",
]


class LogFile(BaseModel):
    path: str
    size_bytes: int
    compressed: bool
    format: LogFormat


class ListLogsResult(BaseModel):
    path: str
    files: list[LogFile]
    total: int
    shown: int
    note: str


Level = Literal["unknown", "debug", "info", "warning", "error", "critical"]
MinLevel = Literal["any", "debug", "info", "warning", "error", "critical"]


class SkippedFile(BaseModel):
    path: str
    reason: str


class ByLevel(BaseModel):
    critical: int
    error: int
    warning: int
    info: int
    debug: int
    unknown: int


class Example(BaseModel):
    file: str
    line: int
    text: str


class Group(BaseModel):
    group_id: str
    format: LogFormat
    level: Level
    pattern: str
    count: int
    first_seen: str | None
    last_seen: str | None
    file_count: int
    files: list[str]
    example: Example


class SummarizeResult(BaseModel):
    scan_id: str
    expires_at: str
    path: str
    since: str | None
    until: str | None
    min_level: MinLevel
    files_scanned: int
    skipped: list[SkippedFile]
    lines_scanned: int
    lines_in_window: int
    first_seen: str | None
    last_seen: str | None
    by_level: ByLevel
    groups: list[Group]
    total_groups: int
    shown: int
    note: str


class SearchMatch(BaseModel):
    file: str
    line: int
    time: str | None
    level: Level
    text: str


class SearchResult(BaseModel):
    path: str
    pattern: str
    matches: list[SearchMatch]
    total: int
    shown: int
    note: str


Severity = Literal["low", "medium", "high", "critical"]


class SaveFindingResult(BaseModel):
    name: str
    path: str
    created: str


class GroupLine(BaseModel):
    file: str
    line: int
    time: str | None
    text: str


class GroupLinesResult(BaseModel):
    scan_id: str
    group_id: str
    pattern: str
    lines: list[GroupLine]
    total: int
    shown: int
    note: str


class NumberedLine(BaseModel):
    line: int
    text: str


class ReadLinesResult(BaseModel):
    file: str
    start: int
    end: int
    total_lines: int
    lines: list[NumberedLine]
