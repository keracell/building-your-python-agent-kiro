"""Command line entry point: parse the flags, check the log root, serve over stdio."""

from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

from . import log_setup, telemetry
from .app import VERSION, create_server
from .auth import token_verifier
from .http import serve


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="log-triage", description="Log Triage MCP server (stdio).")
    parser.add_argument("--root", required=True, metavar="DIR", help="the log root; every path is resolved under it")
    parser.add_argument(
        "--reports", default="reports", metavar="DIR",
        help="where save_finding writes (default: reports in the working directory)",
    )
    parser.add_argument("--read-only", action="store_true", help="do not register save_finding")
    parser.add_argument("--http", metavar="HOST:PORT", help="serve stateless HTTP instead of stdio")
    parser.add_argument(
        "--scan-ttl", type=int, default=900, metavar="SECONDS",
        help="how long a scan_id works, 1 or more (default: 900)",
    )
    parser.add_argument(
        "--log-level", choices=log_setup.LEVELS, default=log_setup.DEFAULT_LEVEL, metavar="LEVEL",
        help="the server's own logging threshold: debug, info, warning or error (default: warning)",
    )
    args = parser.parse_args(argv)
    if args.scan_ttl < 1:
        parser.error("--scan-ttl must be 1 or more")
    if args.http is not None:
        host, separator, port = args.http.rpartition(":")
        if not separator or not host or not port.isascii() or not port.isdigit() or not 1 <= int(port) <= 65535:
            parser.error("--http must be HOST:PORT with a port between 1 and 65535")
        args.http = (host, int(port))
    return args


def root_is_readable(root: str) -> bool:
    path = Path(root)
    return path.is_dir() and os.access(path, os.R_OK | os.X_OK)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not root_is_readable(args.root):
        print(f'log root "{args.root}" is not a readable folder', file=sys.stderr)
        sys.exit(2)
    log_setup.configure(args.log_level)
    telemetry.configure(VERSION)
    auth = None
    if args.http:
        configuration = os.environ.get("LOG_TRIAGE_TOKENS")
        if not configuration:
            print("LOG_TRIAGE_TOKENS is required with --http", file=sys.stderr)
            sys.exit(2)
        try:
            auth = token_verifier(configuration)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)
    server = create_server(args.root, args.reports, args.read_only, args.scan_ttl, auth=auth)
    if args.http:
        serve(server, *args.http)
    else:
        signal.signal(signal.SIGINT, telemetry.flush_and_exit)
        signal.signal(signal.SIGTERM, telemetry.flush_and_exit)
        try:
            server.run(transport="stdio", show_banner=False)
        finally:
            telemetry.shutdown()


if __name__ == "__main__":
    main()
