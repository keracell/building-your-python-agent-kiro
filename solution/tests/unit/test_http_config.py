"""Invalid startup configuration fails without exposing credentials."""

import pytest

from logtriage.__main__ import parse_args
from logtriage.auth import token_verifier


@pytest.mark.parametrize("address", ["localhost", ":8765", "localhost:", "localhost:0", "localhost:65536"])
def test_http_requires_host_and_port(address):
    with pytest.raises(SystemExit) as caught:
        parse_args(["--root", ".", "--http", address])
    assert caught.value.code == 2


def test_bad_token_configuration_does_not_disclose_its_value():
    import secrets

    value = secrets.token_urlsafe(24)
    with pytest.raises(ValueError) as caught:
        token_verifier(value)
    assert value not in str(caught.value)
