"""Paths under the log root, folder walks, and files read into lines."""

from __future__ import annotations

import gzip
import io
import os
from datetime import datetime
from typing import IO, Iterator, NamedTuple

from .formats import detect_format, parse_line, UNKNOWN_FORMAT


class PathRefused(Exception):
    """A path that resolves outside the log root."""


class Line(NamedTuple):
    number: int
    text: str
    time: datetime | None
    level: str
    message: str


def resolve_path(root: str, path: str) -> str:
    """The absolute location of `path` under `root`: relative to it, or absolute inside it."""
    root = os.path.abspath(root)
    target = os.path.abspath(os.path.join(root, path or "."))
    if os.path.commonpath([root, target]) != root:
        raise PathRefused(f"path {path!r} is outside the log root")
    return target


def relative_path(root: str, location: str) -> str:
    """Output form: relative to the root, `/`-separated, `.` for the root itself."""
    return os.path.relpath(location, os.path.abspath(root)).replace(os.sep, "/")


def walk_files(location: str) -> list[str]:
    """The regular files at `location`, or below it, in byte order of their paths; dot names skipped."""
    if os.path.isfile(location):
        return [location]
    found: list[str] = []
    for folder, dirnames, filenames in os.walk(location):
        dirnames[:] = [name for name in dirnames if not name.startswith(".")]
        for name in filenames:
            full = os.path.join(folder, name)
            if not name.startswith(".") and os.path.isfile(full):
                found.append(full)
    found.sort(key=lambda full: os.fsencode(os.path.relpath(full, location)))
    return found


def is_compressed(path: str) -> bool:
    return path.endswith(".gz")


def _open_text(path: str) -> IO[str]:
    raw = gzip.open(path, "rb") if is_compressed(path) else open(path, "rb")
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="\n")


def iter_lines(path: str) -> Iterator[str]:
    """Decoded lines without their terminators; only `\\n` ends a line, and a `\\r` before it is dropped."""
    with _open_text(path) as stream:
        for line in stream:
            if line.endswith("\n"):
                line = line[:-1]
                if line.endswith("\r"):
                    line = line[:-1]
            yield line


def format_of(path: str) -> str:
    return detect_format(iter_lines(path))


def read_lines(path: str, format_name: str) -> list[Line]:
    """Every line of a file with its time, level and message; untimed lines borrow a time."""
    if format_name == UNKNOWN_FORMAT:
        raise ValueError("a file of unknown format has no lines to read")
    parsed: list[tuple[int, str, datetime | None, str, str]] = []
    previous = "unknown"
    for number, text in enumerate(iter_lines(path), start=1):
        moment, level, message = parse_line(format_name, text, previous)
        parsed.append((number, text, moment, level, message))
        previous = level
    current = next((item[2] for item in parsed if item[2] is not None), None)
    lines: list[Line] = []
    for number, text, moment, level, message in parsed:
        if moment is not None:
            current = moment
        lines.append(Line(number, text, current, level, message))
    return lines
