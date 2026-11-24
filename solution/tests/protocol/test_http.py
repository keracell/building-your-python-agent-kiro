"""Exercise authentication and caller isolation through the in-process HTTP stack."""

import asyncio
import secrets

import pytest
from fastmcp.utilities.tests import asgi_server
from fastmcp.exceptions import MCPError

from logtriage.app import create_server
from logtriage.auth import token_verifier


@pytest.fixture
async def http_server(log_root, reports_dir):
    tokens = [secrets.token_urlsafe(24) for _ in range(3)]
    auth = token_verifier(
        f"{tokens[0]}=analyst,{tokens[1]}=analyst,{tokens[2]}=viewer:read-only"
    )
    server = create_server(str(log_root), str(reports_dir), False, auth=auth)
    async with asgi_server(server, stateless_http=True, host_origin_protection=False) as running:
        yield running, tokens


@pytest.mark.parametrize("origin", ["null", "https://localhost", "http://localhost.evil", "http://localhost/"])
async def test_origin_is_checked_before_authentication(http_server, origin):
    server, tokens = http_server
    async with server.http_client() as client:
        for headers in ({}, {"Authorization": f"Bearer {tokens[0]}"}):
            response = await client.post(server.url, headers={**headers, "Origin": origin})
            assert response.status_code == 403


async def test_missing_token_and_valid_local_origin(http_server):
    server, tokens = http_server
    async with server.http_client() as client:
        response = await client.post(server.url, headers={"Origin": "http://localhost:6274"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"].split()[0] == "Bearer"
    async with server.client(auth=tokens[0], headers={"Origin": "http://localhost:6274"}) as client:
        assert len(await client.list_tools()) == 7


async def test_scans_follow_principals_across_connections(http_server, call, refused):
    server, tokens = http_server
    async with server.client(auth=tokens[0]) as first:
        scan = await call(first, "summarize_logs", path="app.log")
    arguments = {"scan_id": scan["scan_id"], "group_id": scan["groups"][0]["group_id"]}
    async with server.client(auth=tokens[1]) as same:
        assert (await call(same, "group_lines", **arguments))["total"] > 0
        assert await same.read_resource(f"triage://scans/{scan['scan_id']}")
    async with server.client(auth=tokens[2]) as other:
        assert "unknown or has expired" in await refused(other, "group_lines", **arguments)
        assert "unknown or has expired" in await refused(other, "timeline", scan_id=scan["scan_id"])
        with pytest.raises(MCPError):
            await other.read_resource(f"triage://scans/{scan['scan_id']}")


async def test_concurrent_callers_keep_independent_scan_caps(http_server, call, refused):
    server, tokens = http_server
    async with server.client(auth=tokens[0]) as analyst, server.client(auth=tokens[2]) as viewer:
        first, other = await asyncio.gather(
            call(analyst, "summarize_logs"), call(viewer, "summarize_logs")
        )
        for _ in range(20):
            await call(analyst, "summarize_logs")
        assert "unknown or has expired" in await refused(analyst, "timeline", scan_id=first["scan_id"])
        assert (await call(viewer, "timeline", scan_id=other["scan_id"]))["total"] > 0


async def test_viewer_cannot_save_but_analyst_can(http_server, call, refused, reports_dir):
    server, tokens = http_server
    arguments = {
        "title": "An observed failure", "severity": "low", "summary": "A synthetic error.",
        "evidence": [{"file": "app.log", "line": 1, "note": "The source line."}],
    }
    async with server.client(auth=tokens[2]) as viewer:
        assert "save_finding" not in {tool.name for tool in await viewer.list_tools()}
        assert await refused(viewer, "save_finding", **arguments) == "save_finding is not available to this caller."
        assert not reports_dir.exists()
    async with server.client(auth=tokens[0]) as analyst:
        assert "save_finding" in {tool.name for tool in await analyst.list_tools()}
        result = await call(analyst, "save_finding", **arguments)
        assert (reports_dir / result["path"]).is_file()


async def test_global_read_only_keeps_unknown_tool_refusal(log_root, reports_dir, refused):
    token = secrets.token_urlsafe(24)
    server = create_server(
        str(log_root), str(reports_dir), True,
        auth=token_verifier(f"{token}=viewer:read-only"),
    )
    async with asgi_server(server, stateless_http=True) as running:
        async with running.client(auth=token) as client:
            text = await refused(client, "save_finding")
            assert text != "save_finding is not available to this caller."
            assert len(await client.list_tools()) == 6
