"""HTTP interaction with the Close challenge endpoint."""

import requests

from close_challenge.exceptions import ChallengeError, SubmissionError

ENDPOINT = "https://api.close.com/buildwithus/"
TIMEOUT = 30


def fetch_challenge(session: requests.Session, url: str = ENDPOINT) -> dict:
    """GET the challenge payload and return it as parsed JSON."""
    response = session.get(url, timeout=TIMEOUT)
    if response.status_code != 200:
        raise ChallengeError(f"GET {url} returned {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ChallengeError("challenge response was not valid JSON") from exc


def submit_digests(
    session: requests.Session,
    digests: list[str],
    url: str = ENDPOINT,
) -> dict:
    """POST the bare digest array, reusing session cookies + CSRF header."""
    headers: dict[str, str] = {}
    csrf = session.cookies.get("_csrf_token")
    if csrf:
        headers["X-CSRFToken"] = csrf
    response = session.post(url, json=digests, headers=headers, timeout=TIMEOUT)
    if response.status_code == 400:
        raise SubmissionError(f"hashes rejected (400): {response.text}")
    if not response.ok:
        raise SubmissionError(
            f"submission failed ({response.status_code}): {response.text}"
        )
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text}
