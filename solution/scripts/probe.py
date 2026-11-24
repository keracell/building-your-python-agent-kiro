"""A scripted client that behaves like a careless host, for checking the server's answers.

It starts the server over stdio with FastMCP's client, sends the five steps of
3-testing-and-debugging/probe-expected.md in order on one session, and prints one line per step:

    step <k> <name>: <tool> -> <outcome>

It exits 0 only when every step got the answer the page names, and 1 otherwise.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import tempfile
from dataclasses import dataclass

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

SCAN_ID = r"s_[0-9a-f]{16}"
WAIT_FOR_EXPIRY_SECONDS = 2.2  # the server runs with --scan-ttl 1

# The contract's error texts (CONTRACT.md, section 5), one expression each, placeholders open. A result with
# isError that does not match one of them is the SDK's refusal, not an error of the tool.
CONTRACT_ERRORS = [re.compile(pattern, re.DOTALL) for pattern in (
    r'path ".*" is outside the log root\. Pass a path relative to the log root; list_logs with path "\." shows what is there\.',
    r'path ".*" does not exist under the log root\. Call list_logs to see what is there\.',
    r'(since|until) must be a date like 2026-01-31 or a time like 2026-01-31T14:00:00Z\.',
    r'until must be later than since\.',
    r'(pattern|value_pattern) is not a valid regular expression\. Escape special characters such as \( \[ \. \* with a backslash, or search for a plain word\.',
    r'scan "s_[0-9a-f]{16}" is unknown or has expired\. Call summarize_logs again for a new scan_id\.',
    r'group "[0-9a-f]{12}" is not in scan "s_[0-9a-f]{16}"\. Use a group_id from that scan\'s groups\.',
    r'line \d+ is past the end of ".*", which has \d+ lines\.',
    r'a finding named ".*" already exists\. Choose a different title\.',
    r'".*" is a folder\. This needs one file; call list_logs to pick one\.',
    r'value_pattern must contain exactly one capture group, for example "size=\(\\d\+\)"\.',
    r'the window needs \d+ buckets and the limit is 500\. Pass a larger bucket_minutes\.',
)]


@dataclass
class Step:
    number: int
    name: str
    tool: str
    arguments: dict
    expected: str  # a full-match expression for the outcome text


def outcome_of(result) -> str:
    """The outcome word of a raw tool result: a contract error is told from an SDK refusal by its text."""
    is_error = getattr(result, "is_error", None)
    if is_error is None:
        is_error = getattr(result, "isError", False)
    structured = getattr(result, "structured_content", None)
    if structured is None:
        structured = getattr(result, "structuredContent", None)
    if is_error:
        text = "".join(block.text for block in result.content if getattr(block, "type", "") == "text")
        if any(pattern.fullmatch(text) for pattern in CONTRACT_ERRORS):
            return f"tool error: {text}"
        return "refused"
    if isinstance(structured, dict) and isinstance(structured.get("scan_id"), str):
        return f"ok scan_id={structured['scan_id']}"
    return "ok"


async def send(session: Client, tool: str, arguments: dict) -> str:
    try:
        return outcome_of(await session.call_tool_mcp(tool, arguments))
    except Exception:  # a JSON-RPC error
        return "refused"


async def first_file(session: Client) -> str:
    """One file of the log root that the server can read, from list_logs."""
    result = await session.call_tool("list_logs", {"limit": 500})
    for entry in result.structured_content["files"]:
        if entry["format"] != "unknown":
            return entry["path"]
    raise SystemExit("probe: the log root holds no readable log file")


def e6(scan_id: str) -> str:
    return re.escape(f'scan "{scan_id}" is unknown or has expired. Call summarize_logs again for a new scan_id.')


async def run(root: str) -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="probe-reports-") as reports:
        transport = StdioTransport(
            command=sys.executable,
            args=["-m", "logtriage", "--root", root, "--scan-ttl", "1", "--reports", reports],
        )
        async with Client(transport) as session:
            path = await first_file(session)
            never_made = "s_0000000000000000"

            def check(step: Step, got: str) -> None:
                print(f"step {step.number} {step.name}: {step.tool} -> {got}", flush=True)
                if not re.fullmatch(step.expected, got, re.DOTALL):
                    failures.append(f"step {step.number} {step.name}: expected {step.expected!r}, got {got!r}")

            # Steps 1 and 2 are sent right away; step 3 waits until the scan of step 2 has expired.
            first = Step(1, "out-of-order", "group_lines", {"scan_id": never_made, "group_id": "000000000000"},
                         "tool error: " + e6(never_made))
            check(first, await send(session, first.tool, first.arguments))

            scan = Step(2, "scan", "summarize_logs", {"path": path, "min_level": "any"}, f"ok scan_id={SCAN_ID}")
            got = await send(session, scan.tool, scan.arguments)
            check(scan, got)
            made = got.removeprefix("ok scan_id=") if got.startswith("ok scan_id=") else never_made

            await asyncio.sleep(WAIT_FOR_EXPIRY_SECONDS)
            expired = Step(3, "expired", "group_lines", {"scan_id": made, "group_id": "000000000000"},
                           "tool error: " + e6(made))
            check(expired, await send(session, expired.tool, expired.arguments))

            unknown = Step(4, "unknown-argument", "list_logs", {"surprise": 1}, "refused")
            check(unknown, await send(session, unknown.tool, unknown.arguments))

            hostile = Step(5, "hostile-path", "read_lines", {"path": "../outside.log", "line": 1},
                           "tool error: " + re.escape(
                               'path "../outside.log" is outside the log root. Pass a path relative to the log root; '
                               'list_logs with path "." shows what is there.'))
            check(hostile, await send(session, hostile.tool, hostile.arguments))
    for failure in failures:
        print(f"probe: {failure}", file=sys.stderr)
    return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Send five careless requests to Log Triage and check the answers.")
    parser.add_argument("--root", required=True, metavar="DIR", help="the log root the server is started with")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.root)))


if __name__ == "__main__":
    main()
