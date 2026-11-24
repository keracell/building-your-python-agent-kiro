"""The reader on the edge cases of 3-testing-and-debugging/tricky-cases.md, one file per format.

Each case is a small hand-built file. Every row holds the line's text and what a correct reader makes of it:
its time, level, message, group pattern and group_id."""

from __future__ import annotations

import pytest

from logtriage.logs.groups import group_id, pattern_of

LONG_MESSAGE = "slow query " + "x" * 1100

# (file name, format, [(text, time, level, message, pattern, group_id)])
CASES = {
    "app": ("billing.log", [
        ("2026-01-15T10:04:12.345Z WARN billing retry 3 of 5 for order 7f3a9c2e-1b4d-4e8a-9c3f-2d1e6b7a8c90 from 192.0.2.10:44321",
         "2026-01-15T10:04:12Z", "warning",
         "retry 3 of 5 for order 7f3a9c2e-1b4d-4e8a-9c3f-2d1e6b7a8c90 from 192.0.2.10:44321",
         "retry <n> of <n> for order <uuid> from <ip>", "33ddc1fe54a2"),
        ("2026-01-15T10:04:13.999Z ERROR billing   charge   failed\tfor  client 0xDEADBEEF hash deadbeefcafe",
         "2026-01-15T10:04:13Z", "error",
         "  charge   failed\tfor  client 0xDEADBEEF hash deadbeefcafe",
         "charge failed for client <n>xDEADBEEF hash <hex>", "d288f6427fda"),
        ("2026-01-15T10:04:14.500Z TRACE billing an unlisted level word",
         "2026-01-15T10:04:13Z", "unknown",
         "2026-01-15T10:04:14.500Z TRACE billing an unlisted level word",
         "<n>-<n>-<n>T<n>:<n>:<n>Z TRACE billing an unlisted level word", "d0dead41d05f"),
        ("2026-01-15T10:04:15.000Z INFO greeter привет 42 мир",
         "2026-01-15T10:04:15Z", "info", "привет 42 мир", "привет <n> мир", "01529d0da3e4"),
        ("2026-01-15T10:04:16.000Z INFO db " + LONG_MESSAGE,
         "2026-01-15T10:04:16Z", "info", LONG_MESSAGE, "slow query " + "x" * 189, "d4c2c0861519"),
    ]),
    "nginx-access": ("access.log", [
        ('192.0.2.10 - - [15/Jan/2026:10:04:12 +0100] "GET /catalog?page=2 HTTP/1.1" 200 512 "-" "curl/8.5.0"',
         "2026-01-15T09:04:12Z", "info", "GET /catalog 200", "GET /catalog <n>", "538e4c29e569"),
        ('192.0.2.10 - - [15/Jan/2026:10:04:13 -0130] "\\x16\\x03" 400 150 "-" "-"',
         "2026-01-15T11:34:13Z", "warning", "- - 400", "- - <n>", "bfa0a90ef849"),
        ('192.0.2.10 - - [15/Jan/2026:10:04:14 +0000] "GET /health HTTP/1.1" 503',
         "2026-01-15T10:04:14Z", "error", "GET /health 503", "GET /health <n>", "3c46eed710c6"),
    ]),
    "nginx-error": ("error.log", [
        ("2026/01/15 10:04:12 [warn] 41#41: *7 an upstream response is buffered to a temporary file",
         "2026-01-15T10:04:12Z", "warning", "an upstream response is buffered to a temporary file",
         "an upstream response is buffered to a temporary file", "3bd48ce6310b"),
        ("2026/01/15 10:04:13 [emerg] 41#41: bind() to 0.0.0.0:80 failed (98: Address already in use)",
         "2026-01-15T10:04:13Z", "critical", "bind() to 0.0.0.0:80 failed (98: Address already in use)",
         "bind() to <ip> failed (<n>: Address already in use)", "83140bb4d9a8"),
    ]),
    "php-fpm": ("php.log", [
        ("[15-Jan-2026 10:04:12] NOTICE: fpm is running, pid 38",
         "2026-01-15T10:04:12Z", "info", "fpm is running, pid 38", "fpm is running, pid <n>", "62b09c437369"),
        ("[31-Feb-2026 10:04:13] WARNING: [pool www] seems busy",
         "2026-01-15T10:04:12Z", "warning", "[pool www] seems busy", "[pool www] seems busy", "ceb290c77a90"),
    ]),
    "postgres": ("postgres.log", [
        ("2026-01-15 10:04:12.345 UTC [2231] DETAIL:  a detail line with nothing before it",
         "2026-01-15T10:04:12Z", "unknown", "a detail line with nothing before it",
         "a detail line with nothing before it", "2373ca066fb5"),
        ("2026-01-15 10:04:13.000 UTC [2231] ERROR:  deadlock detected",
         "2026-01-15T10:04:13Z", "error", "deadlock detected", "deadlock detected", "5025cead45e0"),
        ("2026-01-15 10:04:13.000 UTC [2231] HINT:  See server log for query details.",
         "2026-01-15T10:04:13Z", "error", "See server log for query details.",
         "See server log for query details.", "8bd7e7583a2f"),
        ("2026-01-15 10:04:14.000 UTC [2232] LOG:  checkpoint complete",
         "2026-01-15T10:04:14Z", "info", "checkpoint complete", "checkpoint complete", "2ccd5fdc5598"),
    ]),
    "redis": ("redis.log", [
        ("1:signal-handler (1768471452) Received SIGTERM scheduling shutdown...",
         "2026-01-15T10:04:12Z", "unknown", "1:signal-handler (1768471452) Received SIGTERM scheduling shutdown...",
         "<n>:signal-handler (<hex>) Received SIGTERM scheduling shutdown...", "8b846eee8129"),
        ("1:M 15 Jan 2026 10:04:12.345 - Accepted 192.0.2.10:50000",
         "2026-01-15T10:04:12Z", "debug", "Accepted 192.0.2.10:50000", "Accepted <ip>", "6df934109198"),
        ("1:M 15 Jan 2026 10:04:13.001 * Background saving started by pid 41",
         "2026-01-15T10:04:13Z", "info", "Background saving started by pid 41",
         "Background saving started by pid <n>", "7bfaf9d86945"),
    ]),
    "syslog": ("syslog.log", [
        ("2026-01-15T10:04:12.5-05:30 myhost cron[7][8]: job started",
         "2026-01-15T15:34:12Z", "unknown", "cron[7]: job started", "cron[<n>]: job started", "775320fb57ef"),
        ("2026-01-15T10:04:13.000000+00:00 myhost sshd[812]: Connection closed by 192.0.2.10 port 50122",
         "2026-01-15T10:04:13Z", "unknown", "sshd: Connection closed by 192.0.2.10 port 50122",
         "sshd: Connection closed by <ip> port <n>", "504577a36b8a"),
    ]),
    "pytest": ("pytest.log", [
        ("=== run 2026-01-15T10:00Z ===",
         "2026-01-15T10:00:00Z", "info", "=== run 2026-01-15T10:00Z ===",
         "=== run <n>-<n>-<n>T<n>:<n>Z ===", "324d505f63ef"),
        ("tests/test_cart.py::test_add PASSED",
         "2026-01-15T10:00:00Z", "info", "tests/test_cart.py::test_add PASSED",
         "tests/test_cart.py::test_add PASSED", "e71a9fe27029"),
        ("FAILED tests/test_cart.py::test_remove PASSED",
         "2026-01-15T10:00:00Z", "error", "FAILED tests/test_cart.py::test_remove PASSED",
         "FAILED tests/test_cart.py::test_remove PASSED", "59c0ddfa5eaa"),
        ("   FAILED tests/test_cart.py::test_indented - not a result at the start",
         "2026-01-15T10:00:00Z", "unknown", "FAILED tests/test_cart.py::test_indented - not a result at the start",
         "FAILED tests/test_cart.py::test_indented - not a result at the start", "b38cf9f35d29"),
        ("tests/test_cart.py::test_skip SKIPPED (no network)",
         "2026-01-15T10:00:00Z", "info", "tests/test_cart.py::test_skip SKIPPED (no network)",
         "tests/test_cart.py::test_skip SKIPPED (no network)", "3fda9464f343"),
    ]),
    "gotest": ("gotest.log", [
        ("=== run yesterday ===", None, "info", "=== run yesterday ===", "=== run yesterday ===", "c8eb13dde41d"),
        ("=== RUN   TestCart", None, "debug", "=== RUN   TestCart", "=== RUN TestCart", "e35e78378e72"),
        ("    --- FAIL: TestCart/add (0.01s)", None, "error", "--- FAIL: TestCart/add (0.01s)",
         "--- FAIL: TestCart/add (<n>s)", "412f338effd7"),
        ("    FAIL indented is not a result", None, "unknown", "FAIL indented is not a result",
         "FAIL indented is not a result", "9553fe86cc51"),
        ("ok  \texample.com/shop\t0.004s", None, "info", "ok  \texample.com/shop\t0.004s",
         "ok example.com/shop <n>s", "6a3746714853"),
    ]),
}


def rows() -> list:
    return [
        pytest.param(format_name, number, row, id=f"{format_name}-line{number}")
        for format_name, (_, lines) in CASES.items()
        for number, row in enumerate(lines, start=1)
    ]


@pytest.mark.parametrize("format_name", list(CASES))
def test_the_file_is_detected_as_its_format(read_log, format_name):
    file_name, lines = CASES[format_name]
    detected, _ = read_log(file_name, [row[0] for row in lines])
    assert detected == format_name


@pytest.mark.parametrize("format_name, number, row", rows())
def test_a_line_is_read_as_the_rules_say(read_log, shown, format_name, number, row):
    text, time, level, message, _, _ = row
    file_name, lines = CASES[format_name]
    _, read = read_log(file_name, [r[0] for r in lines])
    line = read[number - 1]
    assert line.number == number
    assert line.text == text
    assert shown(line.time) == time, "time, after untimed lines are filled in"
    assert line.level == level
    assert line.message == message


@pytest.mark.parametrize("format_name, number, row", rows())
def test_a_line_lands_in_the_expected_group(read_log, format_name, number, row):
    _, _, level, _, pattern, expected_id = row
    file_name, lines = CASES[format_name]
    _, read = read_log(file_name, [r[0] for r in lines])
    line = read[number - 1]
    assert pattern_of(line.message) == pattern
    assert group_id(format_name, line.level, pattern_of(line.message)) == expected_id
