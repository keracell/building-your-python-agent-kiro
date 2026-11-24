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


def path_outside(path: str) -> str:
    """E1: the path leaves the log root, holds a NUL byte, or passes through a symlink."""
    return (
        f'path "{path}" is outside the log root. Pass a path relative to the log root; '
        'list_logs with path "." shows what is there.'
    )


def path_missing(path: str) -> str:
    """E2: the path passes screening and does not exist."""
    return f'path "{path}" does not exist under the log root. Call list_logs to see what is there.'


def bad_time(field: str) -> str:
    """E3: since or until does not read as a date or a time."""
    return f"{field} must be a date like 2026-01-31 or a time like 2026-01-31T14:00:00Z."


UNTIL_NOT_LATER = "until must be later than since."  # E4
FINDING_NOT_AVAILABLE = "save_finding is not available to this caller."  # E13


def bad_pattern(field: str) -> str:
    """E5: the regular expression does not compile."""
    return (
        f"{field} is not a valid regular expression. "
        "Escape special characters such as ( [ . * with a backslash, or search for a plain word."
    )


def finding_exists(name: str) -> str:
    """E9: a finding with that name is already saved."""
    return f'a finding named "{name}" already exists. Choose a different title.'


def one_capture_group(field: str) -> str:
    """E11: the value pattern must hold exactly one capture group."""
    return f'{field} must contain exactly one capture group, for example "size=(\\d+)".'


def too_many_buckets(needed: int) -> str:
    """E12: the window needs more buckets than the limit."""
    return f"the window needs {needed} buckets and the limit is 500. Pass a larger bucket_minutes."
