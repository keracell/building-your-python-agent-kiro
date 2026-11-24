"""Resources and templates under triage://: the formats, the saved findings and the stored scans."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import MCPError

from .logs.formats import FORMAT_NAMES
from .scans import LOCAL_CALLER, ScanStore

# What each format's rules can give, from critical down to debug, `unknown` last (docs/log-formats.md).
LEVELS_OF = {
    "app": ["critical", "error", "warning", "info", "debug", "unknown"],
    "nginx-access": ["error", "warning", "info", "unknown"],
    "nginx-error": ["critical", "error", "warning", "info", "debug", "unknown"],
    "php-fpm": ["critical", "error", "warning", "info", "debug", "unknown"],
    "postgres": ["critical", "error", "warning", "info", "debug", "unknown"],
    "redis": ["warning", "info", "debug", "unknown"],
    "syslog": ["unknown"],
    "pytest": ["error", "info", "unknown"],
    "gotest": ["error", "info", "debug", "unknown"],
}

TIMESTAMP_OF = {
    "app": "yyyy-mm-ddTHH:MM:SS.fffZ",
    "nginx-access": "dd/Mon/yyyy:HH:MM:SS ±zzzz",
    "nginx-error": "yyyy/mm/dd HH:MM:SS",
    "php-fpm": "dd-Mon-yyyy HH:MM:SS",
    "postgres": "yyyy-mm-dd HH:MM:SS.fff UTC",
    "redis": "dd Mon yyyy HH:MM:SS.fff",
    "syslog": "yyyy-mm-ddTHH:MM:SS.fff±hh:mm",
    "pytest": "run header",
    "gotest": "run header",
}

# The first line of each format's sample block in docs/log-formats.md that has the format's shape.
EXAMPLE_OF = {
    "app": "2026-01-15T10:04:12.345Z ERROR billing charge failed order=A-1042 amount=19.99 client=192.0.2.10 trace=3f2a9c1e7b6d4a58",
    "nginx-access": '192.0.2.10 - - [15/Jan/2026:10:04:12 +0100] "GET /catalog/items?page=2 HTTP/1.1" 502 157 "-" "curl/8.5.0"',
    "nginx-error": '2026/01/15 10:04:12 [crit] 41#41: *7 open() "/var/www/myhost/cache/a1.tmp" failed (13: Permission denied), client: 192.0.2.10, server: myhost',
    "php-fpm": "[15-Jan-2026 10:04:12] WARNING: [pool www] child 38 exited on signal 9 (SIGKILL) after 12.5 seconds from start",
    "postgres": '2026-01-15 10:04:12.345 UTC [2231] ERROR:  duplicate key value violates unique constraint "users_email_key"',
    "redis": "1:M 15 Jan 2026 10:04:12.345 # WARNING overcommit_memory is set to 0! Background save may fail under low memory condition.",
    "syslog": "2026-01-15T10:04:12.345678+02:00 myhost sshd[812]: Accepted publickey for deploy from 192.0.2.10 port 50122 ssh2",
    "pytest": "=== run 2026-01-15T10:00:00Z ===",
    "gotest": "=== run 2026-01-15T10:00:00Z ===",
}

TITLE_LINE = re.compile(r"^# (.*)$")
SEVERITY_LINE = re.compile(r"^- Severity: (.*)$")
SAVED_LINE = re.compile(r"^- Saved: (.*)$")


def formats_document() -> dict:
    return {
        "formats": [
            {"name": name, "levels": LEVELS_OF[name], "timestamp": TIMESTAMP_OF[name], "example": EXAMPLE_OF[name]}
            for name in FORMAT_NAMES
        ]
    }


def is_report_name(name: str) -> bool:
    """The one rule for a report name, for the list and for a read: no dot, no separator, not empty."""
    return bool(name) and "." not in name and "/" not in name and "\\" not in name and "\0" not in name


def _read_report(reports: str, name: str) -> tuple[str, dict] | None:
    """The saved file's text and its list entry, or None when the list would not show `name`."""
    if not is_report_name(name):
        return None
    path = Path(reports) / f"{name}.md"
    if path.is_symlink() or not path.is_file():
        return None
    text = path.read_bytes().decode("utf-8", errors="replace")
    fields: dict[str, str] = {}
    for line in text.split("\n"):
        for key, pattern in (("title", TITLE_LINE), ("severity", SEVERITY_LINE), ("created", SAVED_LINE)):
            match = pattern.match(line)
            if match and key not in fields:
                fields[key] = match.group(1)
    if len(fields) != 3:
        return None
    return text, {"name": name, **fields}


def reports_document(reports: str) -> dict:
    entries: list[dict] = []
    if os.path.isdir(reports):
        for entry in sorted(os.listdir(reports), key=os.fsencode):
            if entry.endswith(".md"):
                found = _read_report(reports, entry[: -len(".md")])
                if found is not None:
                    entries.append(found[1])
    return {"count": len(entries), "reports": entries}


INVALID_PARAMS = -32602


def _not_found(uri: str) -> MCPError:
    """The contract's resource-not-found error. FastMCP 4.0.3 wraps a plain NotFoundError raised in a
    handler as -32603, so the handler raises the protocol error itself."""
    return MCPError(INVALID_PARAMS, f"Resource not found: {uri}", {"uri": uri})


def register(mcp: FastMCP, reports: str, store: ScanStore) -> None:
    @mcp.resource("triage://formats", mime_type="application/json", description="The nine log formats Log Triage reads.")
    def formats() -> str:
        return json.dumps(formats_document())

    @mcp.resource("triage://reports", mime_type="application/json", description="The saved findings that can be reopened.")
    def report_list() -> str:
        return json.dumps(reports_document(reports))

    @mcp.resource("triage://reports/{name}", mime_type="text/markdown", description="One saved finding, as saved.")
    def report(name: str) -> str:
        found = _read_report(reports, name)
        if found is None:
            raise _not_found(f"triage://reports/{name}")
        return found[0]

    @mcp.resource("triage://scans/{scan_id}", mime_type="application/json", description="The summary of one stored scan.")
    def scan(scan_id: str) -> str:
        stored = store.get(LOCAL_CALLER, scan_id)
        if stored is None:
            raise _not_found(f"triage://scans/{scan_id}")
        return stored.summary.model_dump_json()
