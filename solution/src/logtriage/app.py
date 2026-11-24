"""The Log Triage server object: its name, version, instructions and tools."""

from __future__ import annotations

from fastmcp import FastMCP

from .tools import files, findings, search, summary

NAME = "log-triage"
VERSION = "0.1.0"

INSTRUCTIONS = (
    "Log Triage reads log files under one folder. Start with list_logs to see what is there. "
    "Use summarize_logs on a file or folder, with since and until when you know the time, to get "
    "counts and message groups instead of raw lines. Use search_logs to find the lines that match a "
    "pattern. Record a conclusion with save_finding and cite a file and line for every piece of "
    "evidence. All times are UTC."
)


def create_server(root: str, reports: str, read_only: bool) -> FastMCP:
    """Build the server for a log root and register its tools; the write tool only when not read-only."""
    mcp = FastMCP(name=NAME, version=VERSION, instructions=INSTRUCTIONS)
    files.register(mcp, root)
    summary.register(mcp, root)
    search.register(mcp, root)
    if not read_only:
        findings.register(mcp, reports)
    return mcp
