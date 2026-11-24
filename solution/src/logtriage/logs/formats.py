"""Format detection and the nine formats of docs/log-formats.md."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Callable, Iterable, NamedTuple

from .times import MONTHS, build_time, parse_instant

WHITESPACE = " \t\n\r\f\v"

LEVELS = ("unknown", "debug", "info", "warning", "error", "critical")

# In the order of the detection table: a tie goes to the earlier one.
FORMAT_NAMES = (
    "app", "nginx-access", "nginx-error", "php-fpm", "postgres", "redis", "syslog", "pytest", "gotest",
)
UNKNOWN_FORMAT = "unknown"

SNIFF_LINES = 50


class Parsed(NamedTuple):
    time: datetime | None
    level: str
    message: str


def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.ASCII)


APP = _re(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.\d+Z (DEBUG|INFO|WARN|ERROR|FATAL) \S+ ")
NGINX_ACCESS = _re(r"^\S+ \S+ \S+ \[(\d{2})/([A-Z][a-z]{2})/(\d{4}):(\d{2}):(\d{2}):(\d{2}) ([+-])(\d{2})(\d{2})\] \"")
NGINX_ERROR = _re(r"^(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2}) \[([a-z]+)\] \d+#\d+: ")
PHP_FPM = _re(r"^\[(\d{2})-([A-Z][a-z]{2})-(\d{4}) (\d{2}):(\d{2}):(\d{2})\] ([A-Z]+): ")
POSTGRES = _re(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+ UTC \[\d+\] ([A-Z0-9]+): ")
REDIS = _re(r"^\d+:[XCSM] (\d{2}) ([A-Z][a-z]{2}) (\d{4}) (\d{2}):(\d{2}):(\d{2})\.\d+ ([.\-*#]) ")
SYSLOG = _re(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})\.\d+([+-])(\d{2}):(\d{2}) \S+ ([^\s:]+): ")
PYTEST = _re(r"^=== run \S+ ===$|::\S* (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")
GOTEST = _re(r"^=== run \S+ ===$|^\s*(--- (PASS|FAIL|SKIP):|=== (RUN|PAUSE|CONT) )")

RUN_HEADER = _re(r"^=== run (\S+) ===$")

SNIFF = {
    "app": APP, "nginx-access": NGINX_ACCESS, "nginx-error": NGINX_ERROR, "php-fpm": PHP_FPM,
    "postgres": POSTGRES, "redis": REDIS, "syslog": SYSLOG, "pytest": PYTEST, "gotest": GOTEST,
}


def detect_format(lines: Iterable[str]) -> str:
    """The format of a file from its lines: up to the first 50 non-empty ones, highest count wins."""
    sample: list[str] = []
    for line in lines:
        if line:
            sample.append(line)
            if len(sample) == SNIFF_LINES:
                break
    best, best_count = UNKNOWN_FORMAT, 0
    for name in FORMAT_NAMES:
        count = sum(1 for line in sample if SNIFF[name].search(line))
        if count > best_count:
            best, best_count = name, count
    return best


def _plain(line: str) -> Parsed:
    """A line without its format's shape."""
    return Parsed(None, "unknown", line.strip(WHITESPACE))


def _ints(values: Iterable[str]) -> list[int]:
    return [int(value) for value in values]


def _parse_app(line: str, previous: str) -> Parsed:
    match = APP.search(line)
    if not match:
        return _plain(line)
    year, month, day, hour, minute, second = _ints(match.groups()[:6])
    level = {"FATAL": "critical", "ERROR": "error", "WARN": "warning", "INFO": "info", "DEBUG": "debug"}[match.group(7)]
    return Parsed(build_time(year, month, day, hour, minute, second), level, line[match.end():])


def _parse_nginx_access(line: str, previous: str) -> Parsed:
    match = NGINX_ACCESS.search(line)
    if not match:
        return _plain(line)
    closing = line.find('"', match.end())
    status_match = re.match(r" (\d{3})(?= |$)", line[closing + 1:], re.ASCII) if closing != -1 else None
    if not status_match:
        return _plain(line)
    status = status_match.group(1)
    day, year, hour, minute, second = _ints([match.group(1), match.group(3), match.group(4), match.group(5), match.group(6)])
    month = MONTHS.get(match.group(2))
    moment = None
    if month:
        moment = build_time(year, month, day, hour, minute, second, match.group(7), int(match.group(8)), int(match.group(9)))
    parts = line[match.end():closing].split(" ")
    if len(parts) == 3:
        message = f"{parts[0]} {parts[1].split('?', 1)[0]} {status}"
    else:
        message = f"- - {status}"
    code = int(status)
    level = "error" if code >= 500 else "warning" if code >= 400 else "info"
    return Parsed(moment, level, message)


def _parse_nginx_error(line: str, previous: str) -> Parsed:
    match = NGINX_ERROR.search(line)
    if not match:
        return _plain(line)
    year, month, day, hour, minute, second = _ints(match.groups()[:6])
    levels = {
        "emerg": "critical", "alert": "critical", "crit": "critical", "error": "error",
        "warn": "warning", "notice": "info", "info": "info", "debug": "debug",
    }
    message = re.sub(r"^\*\d+ ", "", line[match.end():], count=1, flags=re.ASCII)
    return Parsed(build_time(year, month, day, hour, minute, second), levels.get(match.group(7), "unknown"), message)


def _parse_php_fpm(line: str, previous: str) -> Parsed:
    match = PHP_FPM.search(line)
    if not match:
        return _plain(line)
    day, year, hour, minute, second = _ints([match.group(1), match.group(3), match.group(4), match.group(5), match.group(6)])
    month = MONTHS.get(match.group(2))
    moment = build_time(year, month, day, hour, minute, second) if month else None
    levels = {"ALERT": "critical", "ERROR": "error", "WARNING": "warning", "NOTICE": "info", "DEBUG": "debug"}
    return Parsed(moment, levels.get(match.group(7), "unknown"), line[match.end():])


POSTGRES_LEVELS = {
    "PANIC": "critical", "FATAL": "critical", "ERROR": "error", "WARNING": "warning",
    "LOG": "info", "INFO": "info", "NOTICE": "info",
    "DEBUG1": "debug", "DEBUG2": "debug", "DEBUG3": "debug", "DEBUG4": "debug", "DEBUG5": "debug",
}
POSTGRES_CONTINUATIONS = {"DETAIL", "HINT", "STATEMENT", "CONTEXT", "QUERY", "LOCATION"}


def _parse_postgres(line: str, previous: str) -> Parsed:
    match = POSTGRES.search(line)
    if not match:
        return _plain(line)
    year, month, day, hour, minute, second = _ints(match.groups()[:6])
    word = match.group(7)
    level = previous if word in POSTGRES_CONTINUATIONS else POSTGRES_LEVELS.get(word, "unknown")
    return Parsed(build_time(year, month, day, hour, minute, second), level, line[match.end():].lstrip(" "))


def _parse_redis(line: str, previous: str) -> Parsed:
    match = REDIS.search(line)
    if not match:
        return _plain(line)
    day, year, hour, minute, second = _ints([match.group(1), match.group(3), match.group(4), match.group(5), match.group(6)])
    month = MONTHS.get(match.group(2))
    moment = build_time(year, month, day, hour, minute, second) if month else None
    level = {"#": "warning", "*": "info", "-": "debug", ".": "debug"}[match.group(7)]
    return Parsed(moment, level, line[match.end():])


def _parse_syslog(line: str, previous: str) -> Parsed:
    match = SYSLOG.search(line)
    if not match:
        return _plain(line)
    year, month, day, hour, minute, second = _ints(match.groups()[:6])
    moment = build_time(year, month, day, hour, minute, second, match.group(7), int(match.group(8)), int(match.group(9)))
    program = re.sub(r"\[\d+\]$", "", match.group(10), flags=re.ASCII)
    return Parsed(moment, "unknown", f"{program}: {line[match.end():]}")


def _run_header(line: str) -> Parsed | None:
    match = RUN_HEADER.search(line)
    if not match:
        return None
    return Parsed(parse_instant(match.group(1)), "info", line.strip(WHITESPACE))


def _parse_pytest(line: str, previous: str) -> Parsed:
    header = _run_header(line)
    if header:
        return header
    result = re.search(r"::\S* (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)", line, re.ASCII)
    if (result and result.group(1) in ("FAILED", "ERROR")) or line.startswith(("FAILED ", "ERROR ")):
        level = "error"
    elif result:
        level = "info"
    else:
        level = "unknown"
    return Parsed(None, level, line.strip(WHITESPACE))


def _parse_gotest(line: str, previous: str) -> Parsed:
    header = _run_header(line)
    if header:
        return header
    if re.match(r"\s*--- FAIL:", line, re.ASCII) or line.startswith("FAIL"):
        level = "error"
    elif re.match(r"\s*--- (PASS|SKIP):", line, re.ASCII) or line.startswith("ok "):
        level = "info"
    elif re.match(r"\s*=== (RUN|PAUSE|CONT) ", line, re.ASCII):
        level = "debug"
    else:
        level = "unknown"
    return Parsed(None, level, line.strip(WHITESPACE))


PARSERS: dict[str, Callable[[str, str], Parsed]] = {
    "app": _parse_app, "nginx-access": _parse_nginx_access, "nginx-error": _parse_nginx_error,
    "php-fpm": _parse_php_fpm, "postgres": _parse_postgres, "redis": _parse_redis,
    "syslog": _parse_syslog, "pytest": _parse_pytest, "gotest": _parse_gotest,
}


def parse_line(format_name: str, line: str, previous_level: str) -> Parsed:
    """Time (None when the line has none of its own), level and message of one line.

    `previous_level` is the level of the line before it in the file; postgres continuation lines take it.
    """
    return PARSERS[format_name](line, previous_level)
