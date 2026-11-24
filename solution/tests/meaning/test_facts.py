"""Meaning tests: the reader and the server against 3-testing-and-debugging/facts.json.

The facts were computed from docs/log-formats.md on the raw files of s3_logs, independently of any server, so a
value that differs is a real difference of reading. Per-line facts go through the reader; the rest goes through
the server's tools. No test here says what happened in the logs: they only check how the files are read."""

from __future__ import annotations

import gzip
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from fastmcp import Client

from logtriage.app import create_server
from logtriage.logs import reader
from logtriage.logs.formats import RUN_HEADER, parse_line
from logtriage.logs.times import UTC, format_time, in_window, parse_instant

REPO = Path(__file__).resolve().parents[3]
S3_LOGS = REPO / "s3_logs"
FACTS = json.loads((REPO / "3-testing-and-debugging" / "facts.json").read_text(encoding="utf-8"))
FILES = FACTS["files"]
IDS = [fact["path"].rsplit("/", 1)[-1] for fact in FILES]
RUN_HEADER_FILES = [fact for fact in FILES if "run_headers" in fact]
NAME_DATE = re.compile(r"-(\d{4}-\d{2}-\d{2})\.log\.gz$")

pytestmark = pytest.mark.skipif(not S3_LOGS.is_dir(), reason="s3_logs is not in this checkout")


def read_file(fact: dict) -> tuple[str, list[reader.Line]]:
    path = str(S3_LOGS / fact["path"])
    format_name = reader.format_of(path)
    return format_name, reader.read_lines(path, format_name)


def own_times(fact: dict, format_name: str) -> list[datetime | None]:
    """The time each line carries itself; None for a line that borrows one."""
    path = str(S3_LOGS / fact["path"])
    return [parse_line(format_name, text, "unknown").time for text in reader.iter_lines(path)]


def shown(moment: datetime | None) -> str | None:
    return None if moment is None else format_time(moment)


@pytest.fixture
async def server_client(tmp_path):
    async with Client(create_server(str(S3_LOGS), str(tmp_path / "reports"), True)) as session:
        yield session


async def summarize(session: Client, **arguments) -> dict:
    result = await session.call_tool("summarize_logs", arguments)
    assert not result.is_error
    return result.structured_content


# ---- facts about files, through the reader ---------------------------------------------------------------------


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_the_format_and_the_line_count(fact):
    format_name, lines = read_file(fact)
    assert format_name == fact["format"]
    assert len(lines) == fact["lines"]
    assert [line.number for line in lines] == list(range(1, fact["lines"] + 1))


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_the_level_counts_over_the_whole_file(fact):
    _, lines = read_file(fact)
    counted = {level: 0 for level in fact["by_level"]}
    for line in lines:
        counted[line.level] += 1
    assert counted == fact["by_level"]


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_lines_with_their_own_time_and_lines_that_borrow_one(fact):
    format_name, lines = read_file(fact)
    own = own_times(fact, format_name)
    assert len(own) == fact["lines"]
    assert sum(moment is not None for moment in own) == fact["lines_with_own_time"]
    assert sum(moment is None for moment in own) == fact["untimed_lines"]
    # a line that borrows a time still gets one, as long as the file has a timed line at all
    assert all(line.time is not None for line in lines)


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_the_first_and_last_own_times(fact):
    format_name, _ = read_file(fact)
    times = [moment for moment in own_times(fact, format_name) if moment is not None]
    assert shown(min(times)) == fact["first_seen"]
    assert shown(max(times)) == fact["last_seen"]


@pytest.mark.parametrize("fact", RUN_HEADER_FILES, ids=[f["path"].rsplit("/", 1)[-1] for f in RUN_HEADER_FILES])
def test_run_headers_and_distinct_run_headers(fact):
    _, lines = read_file(fact)
    headers = [line.text for line in lines if RUN_HEADER.search(line.text)]
    assert len(headers) == fact["run_headers"]
    assert len(set(headers)) == fact["distinct_run_headers"]
    # a run header is the only line of a test log with a time of its own
    assert fact["lines_with_own_time"] == fact["run_headers"]


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_lines_stamped_before_the_date_in_the_file_name(fact):
    format_name, _ = read_file(fact)
    named = datetime.strptime(NAME_DATE.search(fact["path"]).group(1), "%Y-%m-%d").replace(tzinfo=UTC)
    before = sum(1 for moment in own_times(fact, format_name) if moment is not None and moment < named)
    assert before == fact["lines_before_name_date"]


@pytest.mark.parametrize("fact", FILES, ids=IDS)
def test_the_window_with_its_two_edges(fact):
    window = fact["window"]
    since, until = parse_instant(window["since"]), parse_instant(window["until"])
    format_name, lines = read_file(fact)
    own = own_times(fact, format_name)
    # the facts count the lines stamped exactly at each edge by their own time ...
    assert sum(moment == since for moment in own) == window["lines_at_since"]
    assert sum(moment == until for moment in own) == window["lines_at_until"]
    # ... and the lines inside by the time each line has, borrowed or its own: since inclusive, until exclusive
    assert sum(in_window(line.time, since, until) for line in lines) == window["lines_in_window"]
    inside = [line for line in lines if in_window(line.time, since, until)]
    assert all(since <= line.time < until for line in inside)


# ---- facts about answers, through the server's tools -----------------------------------------------------------


@pytest.mark.parametrize("fact", FILES, ids=IDS)
async def test_the_summary_agrees_with_the_facts(server_client, fact):
    result = await summarize(server_client, path=fact["path"], min_level="any", limit=3)
    assert result["files_scanned"] == 1 and result["skipped"] == []
    assert result["lines_scanned"] == fact["lines"]
    assert result["by_level"] == fact["by_level"]
    assert (result["first_seen"], result["last_seen"]) == (fact["first_seen"], fact["last_seen"])


@pytest.mark.parametrize("fact", FILES, ids=IDS)
async def test_the_top_three_groups(server_client, fact):
    result = await summarize(server_client, path=fact["path"], min_level="any", limit=3)
    got = [{"group_id": group["group_id"], "count": group["count"]} for group in result["groups"]]
    assert got == fact["top_groups"]


@pytest.mark.parametrize("fact", FILES, ids=IDS)
async def test_the_window_on_the_server(server_client, fact):
    window = fact["window"]
    inside = await summarize(
        server_client, path=fact["path"], since=window["since"], until=window["until"], min_level="any",
    )
    assert inside["lines_in_window"] == window["lines_in_window"]
    assert inside["since"] == window["since"] and inside["until"] == window["until"]
    # the two edges are one boundary seen from both sides: every line of the file is on one side of `since`
    before = await summarize(server_client, path=fact["path"], until=window["since"], min_level="any")
    from_since = await summarize(server_client, path=fact["path"], since=window["since"], min_level="any")
    assert before["lines_in_window"] + from_since["lines_in_window"] == fact["lines"], (
        "a line is either before `since` or at or after it, never both and never neither"
    )
    after = await summarize(server_client, path=fact["path"], since=window["until"], min_level="any")
    until_edge = await summarize(server_client, path=fact["path"], until=window["until"], min_level="any")
    assert until_edge["lines_in_window"] + after["lines_in_window"] == fact["lines"]


@pytest.mark.parametrize("fact", RUN_HEADER_FILES, ids=[f["path"].rsplit("/", 1)[-1] for f in RUN_HEADER_FILES])
async def test_a_search_finds_every_run_header(server_client, fact):
    found = await server_client.call_tool(
        "search_logs", {"path": fact["path"], "pattern": r"^=== run \S+ ===$", "limit": 1},
    )
    assert found.structured_content["total"] == fact["run_headers"]


@pytest.mark.parametrize("path", FACTS["gz_vs_plain"])
async def test_a_gz_file_reads_like_its_plain_copy(tmp_path, path):
    root = tmp_path / "logs"
    (root / "gz").mkdir(parents=True)
    (root / "plain").mkdir()
    name = path.rsplit("/", 1)[-1]
    shutil.copyfile(S3_LOGS / path, root / "gz" / name)
    (root / "plain" / name[: -len(".gz")]).write_bytes(gzip.decompress((S3_LOGS / path).read_bytes()))
    summaries = {}
    async with Client(create_server(str(root), str(tmp_path / "reports"), True)) as session:
        for side in ("gz", "plain"):
            summary = await summarize(session, path=side, min_level="any", limit=100)
            for group in summary["groups"]:
                group.pop("files")
                group["example"].pop("file")
            summaries[side] = {k: v for k, v in summary.items() if k not in ("scan_id", "expires_at", "path")}
    assert summaries["gz"] == summaries["plain"]
    assert summaries["gz"]["lines_scanned"] > 0
