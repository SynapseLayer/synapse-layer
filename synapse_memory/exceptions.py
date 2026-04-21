"""
Synapse Layer — Exception Hierarchy

Domain-specific exceptions for Synapse Memory backends.
All exceptions inherit from SynapseError for unified catch.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations


class SynapseError(Exception):
    """Base exception for all Synapse Layer errors."""


# ── Forge Backend Exceptions ──────────────────────────────────────────


class ForgeBackendError(SynapseError):
    """Raised when a Forge API request fails.

    Attributes:
        status_code: HTTP status code from Forge API, or None.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)

    def __repr__(self) -> str:
        return f"ForgeBackendError(status={self.status_code}, msg={self.args[0]!r})"


class ForgeAuthError(ForgeBackendError):
    """Raised on 401 Unauthorized — invalid or expired api_key."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class ForgeRateLimitError(ForgeBackendError):
    """Raised on 429 Too Many Requests.

    Attributes:
        retry_after: Seconds to wait before retrying, or None.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, status_code=429)


class ForgeDecryptError(ForgeBackendError):
    """Raised when client-side decryption of a recalled memory fails.

    This may indicate key mismatch, corrupted ciphertext, or
    tampered data.  Never includes sensitive content in message.
    """

    def __init__(self, memory_id: str = "unknown") -> None:
        super().__init__(
            f"Decryption failed for memory {memory_id[:12]}... — possible key mismatch",
            status_code=None,
        )
