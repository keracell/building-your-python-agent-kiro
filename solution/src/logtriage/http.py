"""Stateless HTTP serving with all HTTP diagnostics on stderr."""

import signal
from copy import deepcopy

import uvicorn
from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan

from . import telemetry


def create_http_app(server: FastMCP) -> StarletteWithLifespan:
    return server.http_app(path="/mcp", stateless_http=True, host_origin_protection=False)


def serve(server: FastMCP, host: str, port: int) -> None:
    configuration = deepcopy(uvicorn.config.LOGGING_CONFIG)
    configuration["handlers"]["access"]["stream"] = "ext://sys.stderr"

    def on_signal(sig, frame):
        telemetry.shutdown()
        signal.signal(sig, signal.SIG_DFL)
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)
    try:
        uvicorn.run(create_http_app(server), host=host, port=port, log_config=configuration)
    finally:
        telemetry.shutdown()
