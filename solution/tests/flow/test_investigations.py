"""Whole investigations on one open session: each call uses what the one before returned."""

from __future__ import annotations

import json

from conftest import ERROR_LINES


def counts(scan: dict) -> dict:
    """Everything of a scan that does not change from one scan to the next."""
    return {key: value for key, value in scan.items() if key not in ("scan_id", "expires_at")}


async def test_scan_then_group_then_context(client, call):
    scan = await call(client, "summarize_logs", path="app.log", min_level="error")
    group = scan["groups"][0]
    assert group["level"] == "error" and group["count"] == ERROR_LINES
    lines = await call(client, "group_lines", scan_id=scan["scan_id"], group_id=group["group_id"], limit=200)
    assert lines["total"] == ERROR_LINES and lines["pattern"] == group["pattern"]
    # the group's example is the first line of the group
    first = lines["lines"][0]
    assert (first["file"], first["line"], first["text"]) == (
        group["example"]["file"], group["example"]["line"], group["example"]["text"],
    )
    # read around the last line of the group, and find the same text in the window
    last = lines["lines"][-1]
    context = await call(client, "read_lines", path=last["file"], line=last["line"], before=2, after=2)
    window = {line["line"]: line["text"] for line in context["lines"]}
    assert window[last["line"]] == last["text"]
    assert context["start"] == last["line"] - 2 and context["end"] == last["line"] + 2


async def test_the_same_scan_twice_gives_the_same_counts(client, call):
    request = dict(path=".", min_level="any", since="2026-03-01", until="2026-03-02")
    first = await call(client, "summarize_logs", **request)
    second = await call(client, "summarize_logs", **request)
    assert first["scan_id"] != second["scan_id"]
    assert counts(first) == counts(second)
    # each scan answers from its own handle, with the same group lines
    group = first["groups"][0]["group_id"]
    one = await call(client, "group_lines", scan_id=first["scan_id"], group_id=group, limit=200)
    two = await call(client, "group_lines", scan_id=second["scan_id"], group_id=group, limit=200)
    assert one["lines"] == two["lines"] and one["total"] == two["total"]


async def test_a_search_hit_leads_to_context_and_to_a_report(client, call):
    hits = await call(client, "search_logs", pattern="deadlock")
    assert hits["total"] == 1
    hit = hits["matches"][0]
    context = await call(client, "read_lines", path=hit["file"], line=hit["line"], before=1, after=1)
    assert [line["line"] for line in context["lines"]] == [1, 2, 3]
    saved = await call(
        client, "save_finding", title="Deadlock evidence", severity="medium", summary="One deadlock was logged.",
        evidence=[{"file": hit["file"], "line": hit["line"], "note": hit["text"]}],
    )
    listed = json.loads((await client.read_resource("triage://reports"))[0].text)
    assert [report["name"] for report in listed["reports"]] == [saved["name"]]
    text = (await client.read_resource(f"triage://reports/{saved['name']}"))[0].text
    assert f"`{hit['file']}` line {hit['line']}: {hit['text']}" in text


async def test_a_scan_resource_and_group_lines_agree(client, call):
    scan = await call(client, "summarize_logs", path="postgres.log", min_level="any")
    stored = json.loads((await client.read_resource(f"triage://scans/{scan['scan_id']}"))[0].text)
    assert stored["groups"] == scan["groups"]
    for group in stored["groups"]:
        page = await call(client, "group_lines", scan_id=stored["scan_id"], group_id=group["group_id"])
        assert page["total"] == group["count"]


async def test_the_scan_keeps_its_files_when_a_file_is_added_later(client, call, log_root):
    scan = await call(client, "summarize_logs", path=".", min_level="any")
    group = next(g for g in scan["groups"] if g["level"] == "error" and g["format"] == "app")
    (log_root / "late.log").write_text("2026-03-01T10:00:00.000Z ERROR api upstream timeout after 1ms\n", encoding="utf-8")
    page = await call(client, "group_lines", scan_id=scan["scan_id"], group_id=group["group_id"], limit=200)
    assert page["total"] == ERROR_LINES
    assert {line["file"] for line in page["lines"]} == {"app.log"}
