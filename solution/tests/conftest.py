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


# ---- in-process server and client, on a log root built by hand -------------------------------------------------

import pytest_asyncio
from fastmcp import Client

from logtriage.app import create_server

ERROR_LINES = 12
WARN_LINES = 5
INFO_LINES = 20


def build_log_root(root: Path) -> Path:
    """A small root of two files: an `app` log with three message groups and a `postgres` log."""
    root.mkdir()
    app = [f"2026-03-01T08:{n:02d}:00.000Z ERROR api upstream timeout after {n}00ms" for n in range(1, ERROR_LINES + 1)]
    app += [f"2026-03-01T08:{n + 20:02d}:00.000Z WARN api retry {n} scheduled" for n in range(1, WARN_LINES + 1)]
    app += [f"2026-03-01T09:{n:02d}:00.000Z INFO api request {n} served" for n in range(INFO_LINES)]
    (root / "app.log").write_text("\n".join(app) + "\n", encoding="utf-8")
    postgres = [
        "2026-03-01 08:30:00.000 UTC [100] LOG:  checkpoint complete",
        "2026-03-01 08:31:00.000 UTC [101] ERROR:  deadlock detected",
        "2026-03-01 08:31:00.000 UTC [101] DETAIL:  Process 101 waits for ShareLock",
    ]
    (root / "postgres.log").write_text("\n".join(postgres) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def log_root(tmp_path: Path) -> Path:
    return build_log_root(tmp_path / "logs")


@pytest.fixture
def reports_dir(tmp_path: Path) -> Path:
    return tmp_path / "reports"


@pytest_asyncio.fixture
async def client(log_root: Path, reports_dir: Path):
    """One server and one open session for the test, in the same process."""
    async with Client(create_server(str(log_root), str(reports_dir), False)) as session:
        yield session


@pytest_asyncio.fixture
async def short_lived_client(log_root: Path, reports_dir: Path):
    """The same, with scans that live one second."""
    async with Client(create_server(str(log_root), str(reports_dir), False, scan_ttl=1)) as session:
        yield session


@pytest.fixture
def call():
    """`await call(client, tool, **arguments)`: the structured result of a call that must succeed."""

    async def run(session: Client, tool: str, **arguments):
        result = await session.call_tool(tool, arguments)
        assert not result.is_error
        return result.structured_content

    return run


@pytest.fixture
def refused():
    """`await refused(client, tool, **arguments)`: the text of a call the server answers with an error."""

    async def run(session: Client, tool: str, **arguments) -> str:
        result = await session.call_tool(tool, arguments, raise_on_error=False)
        assert result.is_error
        return result.content[0].text

    return run
