"""Command line entry point: parse the flags, check the log root, serve over stdio."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .app import create_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="log-triage", description="Log Triage MCP server (stdio).")
    parser.add_argument("--root", required=True, metavar="DIR", help="the log root; every path is resolved under it")
    parser.add_argument(
        "--reports", default="reports", metavar="DIR",
        help="where save_finding writes (default: reports in the working directory)",
    )
    parser.add_argument("--read-only", action="store_true", help="do not register save_finding")
    parser.add_argument(
        "--scan-ttl", type=int, default=900, metavar="SECONDS",
        help="how long a scan_id works, 1 or more (default: 900)",
    )
    args = parser.parse_args(argv)
    if args.scan_ttl < 1:
        parser.error("--scan-ttl must be 1 or more")
    return args


def root_is_readable(root: str) -> bool:
    path = Path(root)
    return path.is_dir() and os.access(path, os.R_OK | os.X_OK)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not root_is_readable(args.root):
        print(f'log root "{args.root}" is not a readable folder', file=sys.stderr)
        sys.exit(2)
    create_server(args.root, args.reports, args.read_only, args.scan_ttl).run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
