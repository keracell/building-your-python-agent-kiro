"""Fixtures shared by every layer of the server's own tests."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from logtriage.logs import reader
from logtriage.logs.times import format_time


@pytest.fixture
def write_log(tmp_path: Path) -> Callable[[str, list[str]], Path]:
    """Write a small log file by hand and return its path."""

    def write(name: str, lines: list[str]) -> Path:
        path = tmp_path / name
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return path

    return write


@pytest.fixture
def read_log(write_log: Callable[[str, list[str]], Path]) -> Callable[[str, list[str]], tuple[str, list[reader.Line]]]:
    """Write a file, detect its format and read its lines, the way a scan does."""

    def read(name: str, lines: list[str]) -> tuple[str, list[reader.Line]]:
        path = write_log(name, lines)
        format_name = reader.format_of(str(path))
        return format_name, reader.read_lines(str(path), format_name)

    return read


@pytest.fixture
def shown() -> Callable[[object], str | None]:
    """A time as the tools print it, or None."""
    return lambda moment: None if moment is None else format_time(moment)
