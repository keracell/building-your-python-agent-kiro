"""timeline through the in-process client, on the hand-built root of conftest.py.

The root's `app.log` holds, one line per minute: 12 errors at 08:01 to 08:12 ("upstream timeout after N00ms",
N from 1 to 12), 5 warnings at 08:21 to 08:25 ("retry N scheduled") and 20 infos at 09:00 to 09:19. Every
expected bucket below was counted by hand from that."""

from __future__ import annotations

import pytest

DAY = "2026-03-01T"


def starts(result: dict) -> list[str]:
    return [bucket["start"][len(DAY):] for bucket in result["buckets"]]


def counts(result: dict) -> list[int]:
    return [bucket["count"] for bucket in result["buckets"]]


@pytest.fixture
async def scan(client, call):
    return await call(client, "summarize_logs", path="app.log", min_level="any")


async def test_timeline_is_published_with_its_title_and_hints(client):
    tool = next(tool for tool in await client.list_tools() if tool.name == "timeline")
    assert tool.annotations.read_only_hint is True and tool.annotations.open_world_hint is False
    assert tool.title == "Timeline of matching lines"
    assert 40 <= len(tool.description) <= 400


async def test_every_line_in_the_window_counts_by_hour(client, call, scan):
    result = await call(client, "timeline", scan_id=scan["scan_id"])
    assert (result["start"], result["end"], result["total"]) == (DAY + "08:00:00Z", DAY + "10:00:00Z", 37)
    assert starts(result) == ["08:00:00Z", "09:00:00Z"]
    assert counts(result) == [17, 20]
    assert all(bucket["value_count"] == 0 and bucket["median"] is None for bucket in result["buckets"])
    assert result["pattern"] is None and result["value_pattern"] is None and result["bucket_minutes"] == 60


async def test_a_pattern_counts_only_what_it_matches(client, call, scan):
    result = await call(client, "timeline", scan_id=scan["scan_id"], pattern="timeout")
    assert (result["total"], starts(result), counts(result)) == (12, ["08:00:00Z"], [12])
    assert result["pattern"] == "timeout" and result["end"] == DAY + "09:00:00Z"


async def test_quarter_hour_buckets_include_the_empty_ones(client, call, scan):
    result = await call(client, "timeline", scan_id=scan["scan_id"], bucket_minutes=15)
    assert starts(result) == ["08:00:00Z", "08:15:00Z", "08:30:00Z", "08:45:00Z", "09:00:00Z", "09:15:00Z"]
    assert counts(result) == [12, 5, 0, 0, 15, 5]
    assert result["end"] == DAY + "09:30:00Z" and result["total"] == sum(counts(result))


async def test_the_scans_window_ends_the_grid_and_fills_the_gap(client, call):
    scan = await call(client, "summarize_logs", path="app.log", since=DAY + "08:00", until=DAY + "11:00")
    result = await call(client, "timeline", scan_id=scan["scan_id"])
    assert starts(result) == ["08:00:00Z", "09:00:00Z", "10:00:00Z"]
    assert counts(result) == [17, 20, 0]
    assert (result["start"], result["end"]) == (DAY + "08:00:00Z", DAY + "11:00:00Z")


async def test_the_scans_level_does_not_filter_the_timeline(client, call):
    errors_only = await call(client, "summarize_logs", path="app.log", min_level="error")
    result = await call(client, "timeline", scan_id=errors_only["scan_id"])
    assert result["total"] == 37, "timeline reads every line of the scan's files, whatever min_level the scan had"


async def test_values_are_summarized_per_bucket(client, call, scan):
    result = await call(client, "timeline", scan_id=scan["scan_id"], pattern="timeout", value_pattern=r"after (\d+)ms")
    bucket = result["buckets"][0]
    # the twelve values are 100, 200, ... 1,200: the median is the mean of 600 and 700
    assert (bucket["count"], bucket["value_count"]) == (12, 12)
    assert (bucket["min"], bucket["median"], bucket["max"]) == (100, 650, 1200)
    warnings = await call(client, "timeline", scan_id=scan["scan_id"], pattern="retry", value_pattern=r"retry (\d+)")
    assert (warnings["buckets"][0]["min"], warnings["buckets"][0]["median"], warnings["buckets"][0]["max"]) == (1, 3, 5)


async def test_a_line_that_gives_no_number_still_counts(client, call, scan):
    result = await call(client, "timeline", scan_id=scan["scan_id"], pattern="timeout", value_pattern=r"api (\w+)")
    bucket = result["buckets"][0]
    assert (bucket["count"], bucket["value_count"]) == (12, 0)
    assert (bucket["min"], bucket["median"], bucket["max"]) == (None, None, None)


async def test_a_value_pattern_needs_exactly_one_capture_group(client, call, refused, scan):
    expected = 'value_pattern must contain exactly one capture group, for example "size=(\\d+)".'
    assert await refused(client, "timeline", scan_id=scan["scan_id"], value_pattern=r"after \d+ms") == expected
    assert await refused(client, "timeline", scan_id=scan["scan_id"], value_pattern=r"(a)(b)") == expected
    assert await refused(client, "timeline", scan_id=scan["scan_id"], value_pattern=r"after (?:\d+)ms") == expected


async def test_the_refusals_come_in_the_contracts_order(client, call, refused, scan):
    unknown = "s_0123456789abcdef"
    assert (await refused(client, "timeline", scan_id=unknown, pattern="(", value_pattern="(")).startswith("scan ")
    assert (await refused(client, "timeline", scan_id=scan["scan_id"], pattern="(", value_pattern="(")).startswith("pattern ")
    assert (await refused(client, "timeline", scan_id=scan["scan_id"], value_pattern="(")).startswith("value_pattern is not")


async def test_a_window_that_needs_too_many_buckets_is_refused(client, call, refused):
    scan = await call(client, "summarize_logs", path="app.log", since="2026-03-01", until="2026-03-02")
    text = await refused(client, "timeline", scan_id=scan["scan_id"], bucket_minutes=1)
    assert text == "the window needs 1440 buckets and the limit is 500. Pass a larger bucket_minutes."
    assert (await call(client, "timeline", scan_id=scan["scan_id"], bucket_minutes=3))["total"] == 37
