"""Custom exceptions for the Close challenge."""


class ChallengeError(Exception):
    """Raised when the fetched challenge is missing or malformed."""


class SubmissionError(Exception):
    """Raised when the endpoint rejects the submitted digests."""
