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
