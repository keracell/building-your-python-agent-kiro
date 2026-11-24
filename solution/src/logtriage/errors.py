"""The contract's error texts, each built in one place."""

from __future__ import annotations


def scan_unknown(scan_id: str) -> str:
    """E6: the scan id is unknown, expired, evicted or belongs to another caller."""
    return f'scan "{scan_id}" is unknown or has expired. Call summarize_logs again for a new scan_id.'


def group_not_in_scan(group_id: str, scan_id: str) -> str:
    """E7: the scan does not keep that group."""
    return f'group "{group_id}" is not in scan "{scan_id}". Use a group_id from that scan\'s groups.'


def line_past_end(line: int, file: str, total: int) -> str:
    """E8: the line is past the last line of the file."""
    return f'line {line} is past the end of "{file}", which has {total} lines.'


def is_a_folder(path: str) -> str:
    """E10: a file was needed and the path is a folder."""
    return f'"{path}" is a folder. This needs one file; call list_logs to pick one.'
