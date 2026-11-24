"""Message patterns and group ids."""

from __future__ import annotations

import hashlib
import re

UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", re.ASCII)
IP = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b", re.ASCII)
HEX = re.compile(r"\b[0-9a-fA-F]{8,}\b", re.ASCII)
NUMBER = re.compile(r"\d+(\.\d+)?", re.ASCII)
SPACES = re.compile(r"[ \t\n\r\f\v]+", re.ASCII)


def pattern_of(message: str) -> str:
    """The message with its variable parts replaced, in the seven steps of docs/log-formats.md."""
    text = message[:1000]
    text = UUID.sub("<uuid>", text)
    text = IP.sub("<ip>", text)
    text = HEX.sub("<hex>", text)
    text = NUMBER.sub("<n>", text)
    text = SPACES.sub(" ", text).strip(" ")
    return text[:200]


def group_id(format_name: str, level: str, pattern: str) -> str:
    """The first 12 hex characters of the SHA-256 of format, level and pattern."""
    data = f"{format_name}\n{level}\n{pattern}".encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:12]
