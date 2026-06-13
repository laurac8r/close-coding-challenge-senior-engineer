"""Opt-in live round-trip against the real Close endpoint.

Run explicitly with: uv run pytest -m live
"""

import pytest
import requests

from close_challenge.challenge import parse_challenge
from close_challenge.client import fetch_challenge, submit_digests
from close_challenge.hashing import compute_digests


@pytest.mark.live
def test_live_round_trip() -> None:
    session = requests.Session()
    data = fetch_challenge(session)
    traits, key = parse_challenge(data)
    digests = compute_digests(traits, key)
    result = submit_digests(session, digests)
    assert result  # non-empty verification response
