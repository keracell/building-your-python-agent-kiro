"""The contract's error texts, each built in one place."""

from __future__ import annotations


def scan_unknown(scan_id: str) -> str:
    """E6: the scan id is unknown, expired, evicted or belongs to another caller."""
    return f'scan "{scan_id}" is unknown or has expired. Call summarize_logs again for a new scan_id.'
