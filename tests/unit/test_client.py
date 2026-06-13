"""HTTP client tests — endpoint fully mocked via responses."""

import json

import pytest
import requests
import responses

from close_challenge.client import ENDPOINT, fetch_challenge, submit_digests
from close_challenge.exceptions import ChallengeError, SubmissionError


@responses.activate
def test_fetch_challenge_returns_json() -> None:
    responses.get(ENDPOINT, json={"traits": ["A"], "key": "k"}, status=200)
    assert fetch_challenge(requests.Session(), ENDPOINT) == {
        "traits": ["A"],
        "key": "k",
    }


@responses.activate
def test_fetch_challenge_non_200_raises() -> None:
    responses.get(ENDPOINT, status=500)
    with pytest.raises(ChallengeError, match="500"):
        fetch_challenge(requests.Session(), ENDPOINT)


@responses.activate
def test_fetch_challenge_bad_json_raises() -> None:
    responses.get(ENDPOINT, body="not json", status=200)
    with pytest.raises(ChallengeError, match="JSON"):
        fetch_challenge(requests.Session(), ENDPOINT)


@responses.activate
def test_submit_sends_bare_array_and_csrf_header() -> None:
    responses.post(ENDPOINT, json={"verification_id": "VID-1"}, status=200)
    session = requests.Session()
    session.cookies.set("_csrf_token", "tok123")

    result = submit_digests(session, ["aa", "bb"], ENDPOINT)

    assert result == {"verification_id": "VID-1"}
    posted = responses.calls[-1].request
    assert json.loads(posted.body) == ["aa", "bb"]
    assert posted.headers["X-CSRFToken"] == "tok123"


@responses.activate
def test_submit_no_csrf_cookie_omits_header() -> None:
    responses.post(ENDPOINT, json={"verification_id": "VID-2"}, status=200)
    submit_digests(requests.Session(), ["aa"], ENDPOINT)
    posted = responses.calls[-1].request
    assert "X-CSRFToken" not in posted.headers


@responses.activate
def test_submit_400_raises_submission_error() -> None:
    responses.post(ENDPOINT, body="bad hashes", status=400)
    with pytest.raises(SubmissionError, match="rejected"):
        submit_digests(requests.Session(), ["aa"], ENDPOINT)


@responses.activate
def test_submit_other_error_raises() -> None:
    responses.post(ENDPOINT, body="boom", status=500)
    with pytest.raises(SubmissionError, match="500"):
        submit_digests(requests.Session(), ["aa"], ENDPOINT)
