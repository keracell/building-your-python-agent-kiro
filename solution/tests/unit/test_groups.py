"""The seven grouping steps of docs/log-formats.md and the group id, one step at a time."""

from __future__ import annotations

import hashlib

import pytest

from logtriage.logs.groups import group_id, pattern_of

UUID = "7f3a9c2e-1b4d-4e8a-9c3f-2d1e6b7a8c90"


@pytest.mark.parametrize("message, pattern", [
    # step 2: uuids
    (f"order {UUID} paid", "order <uuid> paid"),
    # step 3: addresses, with their port
    ("from 192.0.2.10:44321 and 10.0.0.1", "from <ip> and <ip>"),
    ("not an address 999.1.1 or 1.2.3", "not an address <n>.<n> or <n>.<n>"),
    # step 4: hex runs of eight or more characters between word boundaries
    ("trace=3f2a9c1e7b6d4a58", "trace=<hex>"),
    ("deadbeef is hex but dead is not", "<hex> is hex but dead is not"),
    # step 5: numbers, with an optional fraction
    ("took 0.25s for 3 items", "took <n>s for <n> items"),
    ("worker v2.10.3", "worker v<n>.<n>"),
    # step 6: runs of whitespace collapse, the ends are trimmed
    ("  a \t b\n\nc  ", "a b c"),
    # the order of the steps shows in these
    ("cache key a1b2c3d4 missed, key a1b2c3 kept", "cache key <hex> missed, key a<n>b<n>c<n> kept"),
    ("upstream 192.0.2.10:8080 timed out (110: Connection timed out)",
     "upstream <ip> timed out (<n>: Connection timed out)"),
    ("1:signal-handler (1768471452) Received SIGINT", "<n>:signal-handler (<hex>) Received SIGINT"),
    ("cart_test.go:42: expected 200, got 404", "cart_test.go:<n>: expected <n>, got <n>"),
], ids=[
    "uuid", "ip-with-port", "short-dotted-run-is-not-an-ip", "hex-run", "hex-needs-eight", "number-fraction",
    "version-number", "whitespace", "hex-before-number", "port-then-number", "epoch-is-hex", "numbers-in-code",
])
def test_pattern_steps(message, pattern):
    assert pattern_of(message) == pattern


def test_ascii_only_digits_and_boundaries():
    """The expressions are compiled with re.ASCII: Arabic-Indic digits are not numbers."""
    assert pattern_of("count ٣ and 3") == "count ٣ and <n>"


def test_the_message_is_cut_to_1000_then_the_pattern_to_200():
    # "z" is not a hex digit, so the run stays a word: only the 200-character cut shows
    assert pattern_of("z" * 1500) == "z" * 200
    # the first cut comes before the whitespace step: the tail past 1,000 characters is never seen
    assert pattern_of("x" + " " * 999 + "tail") == "x"
    assert pattern_of("x" + " " * 998 + "tail") == "x t"  # 1 + 998 + the first letter make 1,000


def test_the_cut_counts_code_points_not_bytes():
    assert pattern_of("я" * 300) == "я" * 200


@pytest.mark.parametrize("format_name, level, pattern", [
    ("app", "error", "charge failed order=A-<n> amount=<n> client=<ip> trace=<hex>"),
    ("syslog", "unknown", "sshd: Accepted publickey for deploy from <ip> port <n> ssh<n>"),
])
def test_group_id_is_a_prefix_of_the_sha256(format_name, level, pattern):
    expected = hashlib.sha256(f"{format_name}\n{level}\n{pattern}".encode("utf-8")).hexdigest()[:12]
    assert group_id(format_name, level, pattern) == expected


@pytest.mark.parametrize("format_name, level, pattern, expected", [
    ("app", "error", "charge failed order=A-<n> amount=<n> client=<ip> trace=<hex>", "6ca6f297d79f"),
    ("app", "info", "session <uuid> expired after <n>s", "c135c047cc96"),
    ("nginx-error", "error", "upstream <ip> timed out (<n>: Connection timed out)", "e0621a880600"),
    ("syslog", "unknown", "sshd: Accepted publickey for deploy from <ip> port <n> ssh<n>", "a70ece346610"),
])
def test_worked_group_ids(format_name, level, pattern, expected):
    assert group_id(format_name, level, pattern) == expected


def test_the_same_pattern_in_another_level_or_format_is_another_group():
    base = group_id("app", "error", "disk full")
    assert group_id("app", "warning", "disk full") != base
    assert group_id("php-fpm", "error", "disk full") != base
    assert group_id("app", "error", "disk full") == base
