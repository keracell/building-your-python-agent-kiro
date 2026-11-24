"""Local bearer-token configuration and the Origin check that precedes it."""

from __future__ import annotations

import re

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from starlette.datastructures import Headers
from starlette.middleware import Middleware
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

LOCAL_ORIGIN = re.compile(r"http://(?:localhost|127\.0\.0\.1)(?::[0-9]+)?")


class OriginGuard:
    """Reject non-local browser origins before authentication is attempted."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            origins = Headers(scope=scope).getlist("origin")
            if any(LOCAL_ORIGIN.fullmatch(origin) is None for origin in origins):
                await Response(status_code=403)(scope, receive, send)
                return
        await self.app(scope, receive, send)


class LocalTokenVerifier(StaticTokenVerifier):
    """Static verification with the contract's stricter Origin policy first."""

    def get_middleware(self) -> list[Middleware]:
        return [Middleware(OriginGuard), *super().get_middleware()]


def token_verifier(configuration: str) -> LocalTokenVerifier:
    """Parse environment configuration without exposing token values in errors."""
    tokens = {}
    for entry in configuration.split(","):
        token, separator, principal = entry.strip().partition("=")
        read_only = principal.endswith(":read-only")
        if read_only:
            principal = principal.removesuffix(":read-only")
        if not separator or not token or not principal or ":" in principal or token in tokens:
            raise ValueError("LOG_TRIAGE_TOKENS must contain token=principal entries")
        tokens[token] = {"client_id": principal, "scopes": ["read-only"] if read_only else []}
    return LocalTokenVerifier(tokens)


def current_caller() -> str:
    """Resolve identity for each request; stdio has the single local caller."""
    token = get_access_token()
    return token.client_id if token is not None else "local"


def caller_is_read_only() -> bool:
    token = get_access_token()
    return token is not None and "read-only" in token.scopes
