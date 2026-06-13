# Close "Build With Us" Challenge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

- **Goal:** Fetch the Close challenge, compute keyed BLAKE2b digests of each
  trait, POST the bare array back, and obtain the Verification ID.

- **Architecture:** Small focused package. Pure hashing logic isolated from I/O;
  challenge parsing/validation separate from HTTP; a thin CLI orchestrates one
  `requests.Session()` so GET cookies (CSRF) carry to the POST.

- **Tech Stack:** Python 3.11+, `requests`, `pytest`, `responses`, `ruff`, `uv`.

---

## File Structure

```
close_challenge/
  __init__.py        # package marker
  exceptions.py      # ChallengeError, SubmissionError
  hashing.py         # pure: compute_digest, compute_digests
  challenge.py       # parse_challenge(data) -> (traits, key)
  client.py          # fetch_challenge (GET), submit_digests (POST), ENDPOINT
  cli.py             # run(url) orchestration + main()
tests/
  unit/
    test_hashing.py
    test_challenge.py
    test_client.py
    test_cli.py
  test_live.py       # opt-in @pytest.mark.live real round-trip
pyproject.toml
```

---

### Task 0: Project scaffold

**Files:**

- Create: `pyproject.toml`
- Create: `close_challenge/__init__.py` (empty)

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "close-challenge"
version = "0.1.0"
description = "Close 'Build With Us' challenge solver"
requires-python = ">=3.11"
dependencies = ["requests>=2.31"]

[dependency-groups]
dev = ["pytest>=8", "responses>=0.25", "ruff>=0.6"]

[tool.pytest.ini_options]
addopts = "-m 'not live'"
markers = ["live: hits the real Close endpoint (opt-in, network)"]

[tool.ruff]
line-length = 88

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create empty package marker**

Create `close_challenge/__init__.py` with a single docstring line:

```python
"""Close 'Build With Us' challenge solver."""
```

- [ ] **Step 3: Sync the environment**

Run: `uv sync`
Expected: creates `.venv`, installs requests + dev deps. Exit 0.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml close_challenge/__init__.py
git commit -m "chore: scaffold close-challenge package"
```

---

### Task 1: Hashing (pure)

**Files:**

- Create: `close_challenge/hashing.py`
- Test: `tests/unit/test_hashing.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_hashing.py`:

```python
"""Golden-vector tests for keyed BLAKE2b hashing (fixed key, not the live one)."""

import pytest

from close_challenge.hashing import compute_digest, compute_digests

# Golden vectors: blake2b(trait.utf8, key=b"test-key", digest_size=64).hexdigest()
CRAFTSMAN = (
    "ab08cf2f32a3d47227c84df01566c2e7216ad957dfa8517050d85a6e55851060"
    "f8da235da3e3e18775ff99664883273439e220e1ea38ccc83be9e733bd0a467d"
)
PRAGMATIC = (
    "1a21a4982171cd30c0a89d20c1755467ecf341e824c10643d717a6795fa7bcf3"
    "d8801a1dcbd817d4b7bb9c6c98491b5b37b84cdd91d86f3c1ec99a913cb08382"
)


@pytest.mark.parametrize(
    "trait, expected",
    [("Craftsman", CRAFTSMAN), ("Pragmatic", PRAGMATIC)],
)
def test_compute_digest_golden(trait: str, expected: str) -> None:
    assert compute_digest(trait, "test-key") == expected


def test_compute_digest_is_128_lowercase_hex() -> None:
    digest = compute_digest("Curious", "test-key")
    assert len(digest) == 128
    assert digest == digest.lower()
    int(digest, 16)  # raises if not valid hex


def test_compute_digests_preserves_order() -> None:
    traits = ["Craftsman", "Pragmatic", "Curious"]
    assert compute_digests(traits, "test-key") == [
        compute_digest(t, "test-key") for t in traits
    ]


def test_compute_digests_empty() -> None:
    assert compute_digests([], "test-key") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_hashing.py -v`
Expected: FAIL — `ModuleNotFoundError: close_challenge.hashing`.

- [ ] **Step 3: Write minimal implementation**

`close_challenge/hashing.py`:

```python
"""Pure BLAKE2b keyed-hash helpers for the Close challenge."""

import hashlib

DIGEST_SIZE = 64


def compute_digest(trait: str, key: str) -> str:
    """Return the lowercase hex BLAKE2b digest of *trait* keyed by *key*."""
    return hashlib.blake2b(
        trait.encode("utf-8"),
        key=key.encode("utf-8"),
        digest_size=DIGEST_SIZE,
    ).hexdigest()


def compute_digests(traits: list[str], key: str) -> list[str]:
    """Return digests for each trait, preserving order."""
    return [compute_digest(trait, key) for trait in traits]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_hashing.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add close_challenge/hashing.py tests/unit/test_hashing.py
git commit -m "feat: keyed blake2b digest helpers with golden-vector tests"
```

---

### Task 2: Exceptions + challenge parsing

**Files:**

- Create: `close_challenge/exceptions.py`
- Create: `close_challenge/challenge.py`
- Test: `tests/unit/test_challenge.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_challenge.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_challenge.py -v`
Expected: FAIL — `ModuleNotFoundError: close_challenge.challenge`.

- [ ] **Step 3: Write minimal implementation**

`close_challenge/exceptions.py`:

```python
"""Custom exceptions for the Close challenge."""


class ChallengeError(Exception):
    """Raised when the fetched challenge is missing or malformed."""


class SubmissionError(Exception):
    """Raised when the endpoint rejects the submitted digests."""
```

`close_challenge/challenge.py`:

```python
"""Parsing and validation of the challenge payload."""

from close_challenge.exceptions import ChallengeError


def parse_challenge(data: dict) -> tuple[list[str], str]:
    """Extract ``(traits, key)`` from a challenge payload, validating shape."""
    if not isinstance(data, dict):
        raise ChallengeError("challenge payload must be a JSON object")
    traits = data.get("traits")
    key = data.get("key")
    if not isinstance(traits, list) or not traits:
        raise ChallengeError("challenge missing non-empty 'traits' list")
    if not all(isinstance(trait, str) for trait in traits):
        raise ChallengeError("all traits must be strings")
    if not isinstance(key, str) or not key:
        raise ChallengeError("challenge missing non-empty 'key' string")
    return traits, key
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_challenge.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add close_challenge/exceptions.py close_challenge/challenge.py tests/unit/test_challenge.py
git commit -m "feat: challenge payload parsing with validation"
```

---

### Task 3: HTTP client (GET + POST)

**Files:**

- Create: `close_challenge/client.py`
- Test: `tests/unit/test_client.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_client.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: close_challenge.client`.

- [ ] **Step 3: Write minimal implementation**

`close_challenge/client.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_client.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add close_challenge/client.py tests/unit/test_client.py
git commit -m "feat: challenge HTTP client with CSRF-aware submission"
```

---

### Task 4: CLI orchestration

**Files:**

- Create: `close_challenge/cli.py`
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Write the failing test**

`tests/unit/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: close_challenge.cli`.

- [ ] **Step 3: Write minimal implementation**

`close_challenge/cli.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add close_challenge/cli.py tests/unit/test_cli.py
git commit -m "feat: CLI orchestration for fetch-hash-submit flow"
```

---

### Task 5: Opt-in live round-trip test

**Files:**

- Create: `tests/test_live.py`

- [ ] **Step 1: Write the live test (skipped by default)**

`tests/test_live.py`:

```python
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
```

- [ ] **Step 2: Verify it is skipped by default**

Run: `uv run pytest tests/test_live.py -v`
Expected: 1 deselected (the `-m 'not live'` default addopts excludes it).

- [ ] **Step 3: Commit**

```bash
git add tests/test_live.py
git commit -m "test: opt-in live round-trip against Close endpoint"
```

---

### Task 6: Full verification + real submission

- [ ] **Step 1: Lint + format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors. (Run `uv run ruff format .` first if needed.)

- [ ] **Step 2: Full unit suite**

Run: `uv run pytest -v`
Expected: all unit tests PASS, live test deselected.

- [ ] **Step 3: Real submission to obtain the Verification ID**

Run: `uv run python -m close_challenge.cli`
Expected: prints `Success! Verification response: ...` containing the
Verification ID. **Capture this ID for the application.**

If it returns a 400: confirm the CSRF header name against the response (try
`X-CSRF-Token` / a CSRF form field) and re-run. This is the one live unknown
flagged in the spec.

- [ ] **Step 4: Record the Verification ID**

Save the returned Verification ID where the application needs it (do not commit
secrets; the ID is a submission token, safe to keep with the application notes).
