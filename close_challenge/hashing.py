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
