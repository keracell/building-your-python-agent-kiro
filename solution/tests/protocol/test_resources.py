"""Every resource and template, read through the in-process client."""

from __future__ import annotations

import json

import pytest
from fastmcp.exceptions import MCPError

NOT_FOUND = -32602


def document(contents) -> dict:
    assert len(contents) == 1
    return json.loads(contents[0].text)


async def test_resources_and_templates_are_listed(client):
    resources = {str(r.uri): r.mime_type for r in await client.list_resources()}
    assert resources == {"triage://formats": "application/json", "triage://reports": "application/json"}
    templates = {t.uri_template: t.mime_type for t in await client.list_resource_templates()}
    assert templates == {"triage://reports/{name}": "text/markdown", "triage://scans/{scan_id}": "application/json"}


async def test_the_formats_document_lists_the_nine_formats(client):
    formats = document(await client.read_resource("triage://formats"))["formats"]
    assert [f["name"] for f in formats] == [
        "app", "nginx-access", "nginx-error", "php-fpm", "postgres", "redis", "syslog", "pytest", "gotest",
    ]
    assert all(f["levels"][-1] == "unknown" and f["timestamp"] and f["example"] for f in formats)


async def test_the_reports_list_is_empty_before_any_finding(client):
    assert document(await client.read_resource("triage://reports")) == {"count": 0, "reports": []}


async def test_a_saved_finding_is_listed_and_readable(client, call):
    saved = await call(
        client, "save_finding", title="Deadlock in postgres", severity="high", summary="Seen once.",
        evidence=[{"file": "postgres.log", "line": 2, "note": "deadlock detected"}],
    )
    listed = document(await client.read_resource("triage://reports"))
    assert listed == {"count": 1, "reports": [{
        "name": "deadlock-in-postgres", "title": "Deadlock in postgres", "severity": "high", "created": saved["created"],
    }]}
    text = (await client.read_resource("triage://reports/deadlock-in-postgres"))[0].text
    assert text.startswith("# Deadlock in postgres\n")


async def test_a_stored_scan_reads_as_the_summary_it_returned(client, call):
    scan = await call(client, "summarize_logs", path="postgres.log", min_level="any")
    assert document(await client.read_resource(f"triage://scans/{scan['scan_id']}")) == scan


@pytest.mark.parametrize("uri", [
    "triage://reports/no-such-finding",
    "triage://reports/a.b",
    "triage://scans/s_0123456789abcdef",
    "triage://nothing/here",
])
async def test_a_missing_resource_is_a_not_found_error_that_names_the_uri(client, uri):
    with pytest.raises(MCPError) as caught:
        await client.read_resource(uri)
    assert caught.value.code == NOT_FOUND
    assert uri in caught.value.message
