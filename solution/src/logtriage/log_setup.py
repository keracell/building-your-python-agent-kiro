"""Logging to stderr, and the middleware that writes one line per tool call.

stdout belongs to the protocol, so every handler here writes to stderr."""

from __future__ import annotations

import logging
import sys

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware
from pydantic import ValidationError

LEVELS = ("debug", "info", "warning", "error")
DEFAULT_LEVEL = "warning"
LOGGER_NAME = "logtriage"

log = logging.getLogger(LOGGER_NAME)


def configure(level: str = DEFAULT_LEVEL) -> None:
    """Send the server's own log lines to stderr at the given threshold."""
    log.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
    log.setLevel(level.upper())
    log.propagate = False


class CallLogMiddleware(Middleware):
    """One `tool=<name>` line at debug for every tools/call, a schema refusal included, because the line is
    written before the call goes on. A masked unexpected error writes its detail at error."""

    async def on_call_tool(self, context, call_next):
        name = context.message.name
        log.debug("tool=%s", name)
        try:
            return await call_next(context)
        except ValidationError:
            raise  # a schema refusal keeps its usual answer
        except ToolError as exc:
            if exc.__cause__ is not None:  # masked: the caller sees only the generic text
                log.error("unexpected error in %s", name, exc_info=exc.__cause__)
            raise
        except Exception:
            log.exception("unexpected error in %s", name)
            raise
