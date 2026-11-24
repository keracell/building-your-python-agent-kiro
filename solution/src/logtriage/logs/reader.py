"""Folder walks and files read into lines."""

from __future__ import annotations

import codecs
import gzip
import os
import zlib
from datetime import datetime
from typing import Iterator, NamedTuple

from .formats import detect_format, parse_line, UNKNOWN_FORMAT

MAX_FILE_BYTES = 67_108_864
MAX_LINE_CHARS = 65_536
CHUNK_BYTES = 1 << 16


class Line(NamedTuple):
    number: int
    text: str
    time: datetime | None
    level: str
    message: str


class Entry(NamedTuple):
    full: str
    symlink: bool


class Unreadable(Exception):
    """A file that cannot be read or decoded, such as a `.gz` file that is not gzip."""


class TooLarge(Exception):
    """A file of more than 64 MiB, decompressed."""


class Skipped(Exception):
    """A file a scan leaves out, with the contract's reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def walk(location: str) -> list[Entry]:
    """The regular files at `location`, or below it, in byte order of their paths, and the symlinked entries
    met on the way, which are never followed. Names that start with a dot are left out."""
    if os.path.isfile(location) and not os.path.islink(location):
        return [Entry(location, False)]
    found: list[Entry] = []
    pending = [location]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                if entry.is_symlink():
                    found.append(Entry(entry.path, True))
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    found.append(Entry(entry.path, False))
    found.sort(key=lambda item: os.fsencode(os.path.relpath(item.full, location)))
    return found


def is_compressed(path: str) -> bool:
    return path.endswith(".gz")


def _clean(line: str, terminated: bool) -> str:
    if terminated and line.endswith("\r"):
        line = line[:-1]
    return line[:MAX_LINE_CHARS]


def iter_lines(path: str, max_bytes: int | None = None) -> Iterator[str]:
    """Decoded lines without their terminators; only `\\n` ends a line, and a `\\r` before it is dropped.

    A line is cut at 65,536 characters. With `max_bytes`, a file that decompresses to more than that raises
    TooLarge; a file that cannot be decoded raises Unreadable."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    pending = ""
    total = 0
    try:
        with (gzip.open(path, "rb") if is_compressed(path) else open(path, "rb")) as raw:
            while chunk := raw.read(CHUNK_BYTES):
                total += len(chunk)
                if max_bytes is not None and total > max_bytes:
                    raise TooLarge(path)
                *complete, pending = (pending + decoder.decode(chunk)).split("\n")
                for line in complete:
                    yield _clean(line, True)
            pending += decoder.decode(b"", final=True)
    except (gzip.BadGzipFile, EOFError, OSError, zlib.error):
        raise Unreadable(path) from None
    if pending:
        yield _clean(pending, False)


def format_of(path: str) -> str:
    """The detected format; raises Unreadable when the lines detection reads do not decode."""
    return detect_format(iter_lines(path))


def read_lines(path: str, format_name: str) -> list[Line]:
    """Every line of a file with its time, level and message; untimed lines borrow a time.

    Raises TooLarge or Unreadable; nothing is returned for a file that fails halfway."""
    if format_name == UNKNOWN_FORMAT:
        raise ValueError("a file of unknown format has no lines to read")
    if not is_compressed(path) and os.stat(path).st_size > MAX_FILE_BYTES:
        raise TooLarge(path)
    parsed: list[tuple[int, str, datetime | None, str, str]] = []
    previous = "unknown"
    for number, text in enumerate(iter_lines(path, MAX_FILE_BYTES), start=1):
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


def load_for_scan(entry: Entry) -> tuple[str, list[Line]]:
    """A file as a scan reads it, or Skipped with the reason. The order of the contract: a symlinked entry,
    then detection, then what is met while reading."""
    if entry.symlink:
        raise Skipped("symlink")
    try:
        format_name = format_of(entry.full)
    except Unreadable:
        raise Skipped("unreadable") from None
    if format_name == UNKNOWN_FORMAT:
        raise Skipped("unknown format")
    try:
        return format_name, read_lines(entry.full, format_name)
    except TooLarge:
        raise Skipped("too large") from None
    except Unreadable:
        raise Skipped("unreadable") from None
