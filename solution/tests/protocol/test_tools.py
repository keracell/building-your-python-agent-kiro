"""Every tool, called through the in-process client: the published surface and a normal answer from each."""

from __future__ import annotations

from conftest import ERROR_LINES, INFO_LINES, WARN_LINES

TOOLS = ["list_logs", "summarize_logs", "search_logs", "group_lines", "read_lines", "save_finding"]
READ_ONLY = TOOLS[:5]


async def test_the_server_publishes_six_tools_with_titles_and_hints(client):
    tools = {tool.name: tool for tool in await client.list_tools()}
    assert sorted(tools) == sorted(TOOLS)
    for name in READ_ONLY:
        hints = tools[name].annotations
        assert hints.read_only_hint is True and hints.open_world_hint is False, name
    assert tools["save_finding"].annotations.destructive_hint is False
    assert all(40 <= len(tool.description) <= 400 for tool in tools.values())
    assert all(tool.output_schema for tool in tools.values())


async def test_list_logs_lists_files_and_formats(client, call):
    result = await call(client, "list_logs")
    assert result["total"] == 2 and result["shown"] == 2 and result["note"] == ""
    assert [(f["path"], f["format"]) for f in result["files"]] == [("app.log", "app"), ("postgres.log", "postgres")]


async def test_summarize_logs_counts_and_groups(client, call):
    result = await call(client, "summarize_logs", path="app.log", min_level="any")
    assert result["files_scanned"] == 1 and result["skipped"] == []
    assert result["lines_scanned"] == result["lines_in_window"] == ERROR_LINES + WARN_LINES + INFO_LINES
    assert result["by_level"] == {
        "critical": 0, "error": ERROR_LINES, "warning": WARN_LINES, "info": INFO_LINES, "debug": 0, "unknown": 0,
    }
    assert [group["count"] for group in result["groups"]] == [INFO_LINES, ERROR_LINES, WARN_LINES]
    assert result["scan_id"].startswith("s_") and result["expires_at"].endswith("Z")


async def test_summarize_logs_window_and_level(client, call):
    result = await call(
        client, "summarize_logs", path="app.log", since="2026-03-01T08:00", until="2026-03-01T09:00",
    )
    assert result["lines_in_window"] == ERROR_LINES + WARN_LINES
    assert [group["level"] for group in result["groups"]] == ["error", "warning"]
    errors_only = await call(client, "summarize_logs", path="app.log", min_level="error")
    assert errors_only["total_groups"] == 1


async def test_search_logs_pages_when_total_is_larger_than_the_page(client, call):
    first = await call(client, "search_logs", path="app.log", pattern="timeout", limit=5)
    assert (first["total"], first["shown"]) == (ERROR_LINES, 5)
    assert first["note"] == "Showing 5 of 12 matches. Pass offset=5 for more."
    assert [m["line"] for m in first["matches"]] == [1, 2, 3, 4, 5]
    last = await call(client, "search_logs", path="app.log", pattern="timeout", limit=5, offset=10)
    assert (last["total"], last["shown"], last["note"]) == (ERROR_LINES, 2, "")
    assert [m["line"] for m in last["matches"]] == [11, 12]


async def test_search_logs_filters_by_level_and_pattern_anywhere_in_the_line(client, call):
    result = await call(client, "search_logs", pattern="(?i)RETRY", min_level="warning")
    assert result["total"] == WARN_LINES
    assert all(m["level"] == "warning" and m["file"] == "app.log" for m in result["matches"])


async def test_group_lines_pages_one_group_of_a_scan(client, call):
    scan = await call(client, "summarize_logs", path="app.log", min_level="any")
    errors = next(g for g in scan["groups"] if g["level"] == "error")
    page = await call(client, "group_lines", scan_id=scan["scan_id"], group_id=errors["group_id"], limit=10)
    assert (page["total"], page["shown"]) == (ERROR_LINES, 10)
    assert page["note"] == "Showing 10 of 12 lines. Pass offset=10 for more."
    assert [line["line"] for line in page["lines"]] == list(range(1, 11))
    rest = await call(client, "group_lines", scan_id=scan["scan_id"], group_id=errors["group_id"], limit=10, offset=10)
    assert [line["line"] for line in rest["lines"]] == [11, 12] and rest["note"] == ""


async def test_read_lines_clips_the_window_to_the_file(client, call):
    result = await call(client, "read_lines", path="app.log", line=2, before=5, after=3)
    assert (result["start"], result["end"], result["total_lines"]) == (1, 5, ERROR_LINES + WARN_LINES + INFO_LINES)
    assert [line["line"] for line in result["lines"]] == [1, 2, 3, 4, 5]
    tail = await call(client, "read_lines", path="postgres.log", line=3, after=200)
    assert (tail["start"], tail["end"], tail["total_lines"]) == (1, 3, 3)


async def test_save_finding_writes_a_report(client, call, reports_dir):
    result = await call(
        client, "save_finding", title="Upstream timeouts", severity="medium", summary="Timeouts at 08:00.",
        evidence=[{"file": "app.log", "line": 1, "note": "the first timeout"}],
    )
    assert result["name"] == "upstream-timeouts" and result["path"] == "upstream-timeouts.md"
    text = (reports_dir / "upstream-timeouts.md").read_text(encoding="utf-8")
    assert text.startswith("# Upstream timeouts\n\n- Severity: medium\n")
    assert text.endswith("- `app.log` line 1: the first timeout\n")
