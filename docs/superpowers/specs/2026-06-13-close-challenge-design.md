# Close "Build With Us" Challenge — Design

**Date:** 2026-06-13
**Endpoint:** `https://api.close.com/buildwithus/`

## Goal

Fetch the challenge from the endpoint, compute the keyed BLAKE2b digest of each
trait, and POST the bare JSON array of digests back to the same endpoint to
receive a Verification ID.

## The challenge (verbatim intent)

> Using the included UTF-8 `key`, construct a JSON array using the lowercase hex
> digest of the blake2b hash for each trait (digest size=64). POST this bare
> array back to this endpoint. 400 responses indicate a problem with the hashes.
> The key rotates each day around midnight EST.

Confirmed GET response shape:

```json
{
    "traits": [
        "Craftsman",
        "Pragmatic",
        "Curious",
        "Methodical",
        "Driven",
        "Collaborator"
    ],
    "key": "Close-d0278a75",
    "meta": {
        "description": "..."
    }
}
```

The GET response sets two cookies — `_csrf_token` and `session` — that the POST
almost certainly requires.

## Hash definition

For each trait:

```python
hashlib.blake2b(
    trait.encode("utf-8"),
    key=key.encode("utf-8"),
    digest_size=64,
).hexdigest()
```

`digest_size=64` → 64 bytes → **128 lowercase hex characters** per digest.
`hexdigest()` is already lowercase.

## Data source decision

**GET-only.** Always fetch fresh traits + key from the endpoint at submission
time (no local-file fallback). The key rotates daily, so a stale
`coding-challenge.json` would yield 400s; fetching fresh sidesteps that. Error
out if the GET is unavailable.

## Architecture

Small focused package, one concern per module. Pure logic isolated from I/O for
clean unit testing.

| Module                   | Responsibility                                                                                                                                                                    |
|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `hashing.py`             | Pure. `compute_digest(trait, key) -> str`, `compute_digests(traits, key) -> list[str]`. No I/O.                                                                                   |
| `challenge.py`           | `parse_challenge(data: dict) -> tuple[list[str], str]`. Validates shape; raises on bad input.                                                                                     |
| `client.py`              | `fetch_challenge(session, url) -> dict` (GET), `submit_digests(session, url, digests) -> dict` (POST). Carries session cookies + `X-CSRFToken` header when the cookie is present. |
| `exceptions.py`          | `ChallengeError`, `SubmissionError`.                                                                                                                                              |
| `cli.py` / `__main__.py` | Orchestrates one `Session()`: GET → parse → hash → POST → print Verification ID.                                                                                                  |

## Data flow

```
requests.Session()
  → fetch_challenge(session, URL)      # GET; captures _csrf_token + session cookies
  → parse_challenge(data)              # (traits, key)
  → compute_digests(traits, key)       # list[str] of 128-hex digests
  → submit_digests(session, URL, digests)  # POST bare array, same session
  → print Verification ID
```

## Error handling

- Custom exceptions in `exceptions.py`; validate early, raise immediately. No
  bare `except`.
- GET non-200 or non-JSON body → `ChallengeError`.
- Missing/wrong-typed `traits` or `key` → `ChallengeError`.
- POST 400 → `SubmissionError` carrying the response body ("hashes rejected").
- POST other non-2xx → `SubmissionError`.
- CLI catches these, prints a clear message, exits non-zero.

## CSRF handling

The POST reuses the same `requests.Session()` as the GET, so `_csrf_token` and
`session` cookies are sent automatically. Additionally, when a `_csrf_token`
cookie is present, send it as the `X-CSRFToken` request header (Flask/Pyramid
convention). Confirm the exact requirement against the live 200/400 during the
real submission; adjust header name if needed.

## Testing (TDD, RED → GREEN)

- **`hashing`** — golden-vector unit tests against a *fixed* key/trait (NOT the
  live rotating key) so the test is stable: assert exact 128-char lowercase hex
  output, length, and charset. Parametrized.
- **`challenge`** — valid parse + each malformed-input raise path via
  `pytest.raises(..., match=...)`.
- **`client`** — HTTP fully mocked (`responses`). Verify: GET cookies are reused
  on the POST, `X-CSRFToken` header is sent, POST body is the bare array,
  200 → returns Verification ID, 400 → `SubmissionError`.
- **One opt-in live e2e** — marked (e.g. `@pytest.mark.live`), skipped by
  default, that performs the real GET → hash → POST round-trip.

## Tooling

- `uv` environment, local `.venv`.
- `ruff check` + `ruff format` (88-col), `pytest`.
- Dependencies: `requests`; dev: `pytest`, `responses`.
- Python 3.11+ type hints throughout (`list[str]`, `X | None`).

## Out of scope (YAGNI)

- Retry/backoff (ratelimit is 100/window — irrelevant for ~2 calls).
- Local-file fallback (GET-only by decision).
- Persisting the Verification ID anywhere — just print it.
