"""End-to-end CLI orchestration tests — endpoint mocked."""

import json

import responses

from close_challenge.cli import run
from close_challenge.client import ENDPOINT
from close_challenge.hashing import compute_digests


@responses.activate
def test_run_happy_path_posts_correct_digests() -> None:
    responses.get(
        ENDPOINT,
        json={"traits": ["Craftsman", "Pragmatic"], "key": "test-key"},
        status=200,
    )
    responses.post(ENDPOINT, json={"verification_id": "VID-9"}, status=200)

    exit_code = run(ENDPOINT)

    assert exit_code == 0
    posted = responses.calls[-1].request
    assert json.loads(posted.body) == compute_digests(
        ["Craftsman", "Pragmatic"], "test-key"
    )


@responses.activate
def test_run_returns_1_on_400() -> None:
    responses.get(ENDPOINT, json={"traits": ["A"], "key": "k"}, status=200)
    responses.post(ENDPOINT, body="bad", status=400)
    assert run(ENDPOINT) == 1


@responses.activate
def test_run_returns_1_on_bad_challenge() -> None:
    responses.get(ENDPOINT, json={"nope": True}, status=200)
    assert run(ENDPOINT) == 1
