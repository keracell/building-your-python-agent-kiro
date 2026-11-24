"""The scan store: scans kept in memory for a while, under a random id, for the caller that made them."""

from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MAX_SCANS_PER_CALLER = 20
MAX_LINES_PER_GROUP = 10_000
LOCAL_CALLER = "local"


@dataclass
class StoredGroup:
    """A group of a scan: its full count and where its first lines are (relative path, line number)."""

    pattern: str
    count: int
    positions: list[tuple[str, int]]


@dataclass
class ScannedFile:
    full: str  # absolute location when the scan read it
    format: str


@dataclass
class Scan:
    scan_id: str
    caller: str
    deadline: float  # on the store's monotonic clock
    request: dict[str, Any]
    summary: Any  # the summarize_logs result that was returned
    files: dict[str, ScannedFile]  # the files the scan read, by relative path
    groups: dict[str, StoredGroup]  # every group at or above min_level, by group_id


class ScanStore:
    """Every read and write goes through one lock, so expiry and eviction are decided together."""

    def __init__(self, ttl_seconds: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._scans: dict[str, OrderedDict[str, Scan]] = {}

    def new_id(self) -> str:
        return "s_" + secrets.token_hex(8)

    def add(
        self, caller: str, scan_id: str, request: dict[str, Any], summary: Any,
        files: dict[str, ScannedFile], groups: dict[str, StoredGroup],
    ) -> Scan:
        """Keep a scan. A caller holds at most 20; the oldest goes first, without a word."""
        with self._lock:
            now = self._clock()
            held = self._scans.setdefault(caller, OrderedDict())
            self._drop_expired(held, now)
            scan = Scan(scan_id, caller, now + self.ttl_seconds, request, summary, files, groups)
            held[scan_id] = scan
            while len(held) > MAX_SCANS_PER_CALLER:
                held.popitem(last=False)
            return scan

    def get(self, caller: str, scan_id: str) -> Scan | None:
        """The scan, or None when it is unknown, expired, evicted or another caller's."""
        with self._lock:
            held = self._scans.get(caller)
            if held is None:
                return None
            self._drop_expired(held, self._clock())
            return held.get(scan_id)

    @staticmethod
    def _drop_expired(held: OrderedDict[str, Scan], now: float) -> None:
        for scan_id in [key for key, scan in held.items() if scan.deadline <= now]:
            del held[scan_id]
