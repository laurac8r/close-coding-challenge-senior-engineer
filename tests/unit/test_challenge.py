"""Validation tests for parse_challenge."""

import pytest

from close_challenge.challenge import parse_challenge
from close_challenge.exceptions import ChallengeError


def test_parse_valid() -> None:
    data = {"traits": ["A", "B"], "key": "k", "meta": {}}
    assert parse_challenge(data) == (["A", "B"], "k")


@pytest.mark.parametrize(
    "data, match",
    [
        ({"key": "k"}, "traits"),
        ({"traits": [], "key": "k"}, "traits"),
        ({"traits": "A", "key": "k"}, "traits"),
        ({"traits": [1, 2], "key": "k"}, "strings"),
        ({"traits": ["A"]}, "key"),
        ({"traits": ["A"], "key": ""}, "key"),
        ({"traits": ["A"], "key": 7}, "key"),
    ],
)
def test_parse_invalid(data: dict, match: str) -> None:
    with pytest.raises(ChallengeError, match=match):
        parse_challenge(data)


def test_parse_non_dict() -> None:
    with pytest.raises(ChallengeError, match="object"):
        parse_challenge(["not", "a", "dict"])  # type: ignore[arg-type]
