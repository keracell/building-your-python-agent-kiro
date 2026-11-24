"""Refusals and errors as the caller sees them."""

from __future__ import annotations

import asyncio

import pytest

SECRET_MARKERS = ("Traceback", "/tmp", "logs/")


async def test_a_value_the_schema_refuses_never_reaches_the_handler(client, refused):
    await refused(client, "group_lines", scan_id="scan-1", group_id="0123456789ab")
    await refused(client, "list_logs", limit=0)
    await refused(client, "read_lines", path="app.log", line=1, surprise=True)


@pytest.mark.parametrize("path", ["../outside.log", "/etc/passwd", "app.log\x00"])
async def test_a_path_outside_the_root_is_refused_with_its_text(client, refused, path):
    text = await refused(client, "list_logs", path=path)
    assert text == (
        f'path "{path}" is outside the log root. Pass a path relative to the log root; '
        'list_logs with path "." shows what is there.'
    )


async def test_a_missing_path_is_refused(client, refused):
    text = await refused(client, "read_lines", path="missing.log", line=1)
    assert text == 'path "missing.log" does not exist under the log root. Call list_logs to see what is there.'


async def test_a_folder_and_a_line_past_the_end_are_refused(client, refused):
    assert await refused(client, "read_lines", path=".", line=1) == (
        '"." is a folder. This needs one file; call list_logs to pick one.'
    )
    assert await refused(client, "read_lines", path="postgres.log", line=9) == (
        'line 9 is past the end of "postgres.log", which has 3 lines.'
    )


async def test_bad_windows_and_patterns_are_refused(client, refused):
    assert await refused(client, "summarize_logs", since="yesterday") == (
        "since must be a date like 2026-01-31 or a time like 2026-01-31T14:00:00Z."
    )
    assert await refused(client, "search_logs", pattern=".", since="2026-03-02", until="2026-03-01") == (
        "until must be later than since."
    )
    assert (await refused(client, "search_logs", pattern="quota(")).startswith("pattern is not a valid regular expression.")


async def test_an_unknown_scan_and_an_unknown_group_are_refused(client, call, refused):
    unknown = "s_0123456789abcdef"
    assert await refused(client, "group_lines", scan_id=unknown, group_id="0123456789ab") == (
        f'scan "{unknown}" is unknown or has expired. Call summarize_logs again for a new scan_id.'
    )
    scan = await call(client, "summarize_logs", path="app.log")
    text = await refused(client, "group_lines", scan_id=scan["scan_id"], group_id="0123456789ab")
    assert text == f'group "0123456789ab" is not in scan "{scan["scan_id"]}". Use a group_id from that scan\'s groups.'


async def test_a_scan_expires(short_lived_client, call, refused):
    scan = await call(short_lived_client, "summarize_logs", path="app.log")
    group = scan["groups"][0]["group_id"]
    await call(short_lived_client, "group_lines", scan_id=scan["scan_id"], group_id=group)
    await asyncio.sleep(1.3)
    text = await refused(short_lived_client, "group_lines", scan_id=scan["scan_id"], group_id=group)
    assert text.startswith(f'scan "{scan["scan_id"]}" is unknown or has expired.')


async def test_an_existing_finding_is_never_overwritten(client, call, refused, reports_dir):
    evidence = [{"file": "app.log", "line": 1, "note": "first"}]
    await call(client, "save_finding", title="Same name", severity="low", summary="One.", evidence=evidence)
    before = (reports_dir / "same-name.md").read_bytes()
    text = await refused(client, "save_finding", title="Same name!", severity="high", summary="Two.", evidence=evidence)
    assert text == 'a finding named "same-name" already exists. Choose a different title.'
    assert (reports_dir / "same-name.md").read_bytes() == before


async def test_evidence_is_checked_before_anything_is_written(client, refused, reports_dir):
    evidence = [
        {"file": "app.log", "line": 1, "note": "fine"},
        {"file": "app.log", "line": 999, "note": "past the end"},
    ]
    text = await refused(client, "save_finding", title="Bad evidence", severity="low", summary="x", evidence=evidence)
    assert text.startswith("line 999 is past the end of \"app.log\"")
    assert not reports_dir.exists() or list(reports_dir.iterdir()) == []


async def test_an_unexpected_error_is_masked(log_root, refused, tmp_path):
    from fastmcp import Client
    from logtriage.app import create_server

    (log_root / "broken.log.gz").write_bytes(b"not gzip data\n")
    async with Client(create_server(str(log_root), str(tmp_path / "reports"), False)) as session:
        text = await refused(session, "read_lines", path="broken.log.gz", line=1)
    assert text == "Error calling tool 'read_lines'"
    assert not any(marker in text for marker in SECRET_MARKERS)
