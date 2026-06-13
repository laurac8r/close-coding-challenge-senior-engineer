"""Command-line entry point for the Close challenge."""

import sys

import requests

from close_challenge.challenge import parse_challenge
from close_challenge.client import ENDPOINT, fetch_challenge, submit_digests
from close_challenge.exceptions import ChallengeError, SubmissionError
from close_challenge.hashing import compute_digests


def run(url: str = ENDPOINT) -> int:
    """Fetch, hash, submit; print the result. Return a process exit code."""
    session = requests.Session()
    try:
        data = fetch_challenge(session, url)
        traits, key = parse_challenge(data)
        digests = compute_digests(traits, key)
        result = submit_digests(session, digests, url)
    except (ChallengeError, SubmissionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        return 1
    print(f"Success! Verification response: {result}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
