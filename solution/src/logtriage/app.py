"""The Log Triage server object: its name, version, instructions and tools."""

from __future__ import annotations

from fastmcp import FastMCP

from .scans import ScanStore
from .tools import context, files, findings, search, summary

NAME = "log-triage"
VERSION = "0.2.0"

INSTRUCTIONS = (
    "Log Triage reads log files under one folder. Start with list_logs to see what is there. "
    "Use summarize_logs on a file or folder, with since and until when you know the time, to get "
    "counts and message groups instead of raw lines. Use search_logs to find the lines that match a "
    "pattern. Record a conclusion with save_finding and cite a file and line for every piece of "
    "evidence. All times are UTC."
)


def lifetime_text(seconds: int) -> str:
    """The exact configured lifetime: whole minutes only when divisible by 60, seconds otherwise."""
    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    return f"{seconds} second" if seconds == 1 else f"{seconds} seconds"


def instructions_for(scan_ttl: int) -> str:
    return (
        f"{INSTRUCTIONS} summarize_logs returns a scan_id that works for {lifetime_text(scan_ttl)}; "
        "pass it to group_lines to read one group's lines without scanning again. "
        "Use read_lines for the lines around one line. Saved findings are listed at triage://reports."
    )


def create_server(root: str, reports: str, read_only: bool, scan_ttl: int = 900) -> FastMCP:
    """Build the server for a log root and register its tools; the write tool only when not read-only."""
    mcp = FastMCP(name=NAME, version=VERSION, instructions=instructions_for(scan_ttl))
    store = ScanStore(scan_ttl)
    files.register(mcp, root)
    summary.register(mcp, root, store)
    search.register(mcp, root)
    context.register(mcp, store)
    if not read_only:
        findings.register(mcp, reports)
    return mcp
