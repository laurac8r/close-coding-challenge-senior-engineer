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
