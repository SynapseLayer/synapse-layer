"""
Synapse Layer — AES-256-GCM Encryption

Provides authenticated encryption with associated data (AEAD)
using AES-256-GCM via the `cryptography` library.

Wire format (all big-endian)::

    [ 1 byte version ][ 12 bytes nonce ][ N bytes ciphertext+tag ]

    - version:    0x01 (current)
    - nonce:      96-bit random IV
    - ciphertext: AES-256-GCM output (includes 128-bit auth tag)

Key derivation uses PBKDF2-HMAC-SHA256 with 600,000 iterations
(OWASP 2023 recommendation) and a 16-byte random salt.

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import hashlib
import logging
import os
import struct
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

_VERSION = 0x01
_NONCE_BYTES = 12     # 96-bit nonce (GCM standard)
_KEY_BYTES = 32       # AES-256
_PBKDF2_ITERATIONS = 600_000  # OWASP 2023
_SALT_BYTES = 16


class SynapseCrypto:
    """AES-256-GCM authenticated encryption for SynapseMemory.

    Thread-safe.  Instances are immutable after construction.

    Args:
        key: 32-byte AES-256 key.  Use :meth:`generate_key` or
             :meth:`from_password` to create one.
    """

    __slots__ = ("_key", "_aesgcm")

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, bytes) or len(key) != _KEY_BYTES:
            raise ValueError(
                f"Key must be {_KEY_BYTES} bytes, got {len(key) if isinstance(key, bytes) else type(key).__name__}"
            )
        self._key = key
        self._aesgcm = AESGCM(key)
        logger.debug("SynapseCrypto initialized (key fingerprint: %s)",
                     hashlib.sha256(key).hexdigest()[:12])

    # ── Factory methods ───────────────────────────────────────────────

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically secure random 256-bit key."""
        return os.urandom(_KEY_BYTES)

    @classmethod
    def from_password(
        cls,
        password: Union[str, bytes],
        salt: Optional[bytes] = None,
        iterations: int = _PBKDF2_ITERATIONS,
    ) -> "SynapseCrypto":
        """Derive a 256-bit key from a password using PBKDF2-HMAC-SHA256.

        Args:
            password: User password (str or bytes).
            salt: 16-byte salt.  If None, generates a random one.
                  **Store the salt alongside your ciphertext** if you
                  need to decrypt later with the same password.
            iterations: PBKDF2 iteration count.  Default: 600,000.

        Returns:
            (SynapseCrypto, salt) if salt was generated, else SynapseCrypto.
        """
        if isinstance(password, str):
            password = password.encode("utf-8")

        if salt is None:
            salt = os.urandom(_SALT_BYTES)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=_KEY_BYTES,
            salt=salt,
            iterations=iterations,
        )
        key = kdf.derive(password)
        return cls(key)

    @classmethod
    def from_env(
        cls,
        env_var: str = "SYNAPSE_ENCRYPTION_KEY",
    ) -> Optional["SynapseCrypto"]:
        """Create from hex-encoded key in environment variable.

        Returns None if the variable is not set.
        """
        raw = os.environ.get(env_var)
        if not raw:
            return None
        key = bytes.fromhex(raw)
        return cls(key)

    # ── Encrypt / Decrypt ─────────────────────────────────────────────

    def encrypt(
        self,
        plaintext: Union[str, bytes],
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Encrypt plaintext with AES-256-GCM.

        Args:
            plaintext: Data to encrypt (str auto-encoded as UTF-8).
            associated_data: Optional AAD (authenticated but not encrypted).

        Returns:
            Wire-format bytes: [version][nonce][ciphertext+tag].
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        nonce = os.urandom(_NONCE_BYTES)
        ct = self._aesgcm.encrypt(nonce, plaintext, associated_data)

        return struct.pack("B", _VERSION) + nonce + ct

    def decrypt(
        self,
        ciphertext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt AES-256-GCM ciphertext.

        Args:
            ciphertext: Wire-format bytes from :meth:`encrypt`.
            associated_data: Must match the AAD used during encryption.

        Returns:
            Original plaintext bytes.

        Raises:
            ValueError: If version is unsupported or data is corrupted.
            cryptography.exceptions.InvalidTag: If auth tag fails.
        """
        min_len = 1 + _NONCE_BYTES + 16  # version + nonce + min GCM tag
        if len(ciphertext) < min_len:
            raise ValueError(
                f"Ciphertext too short ({len(ciphertext)} bytes, minimum {min_len})"
            )

        version = ciphertext[0]
        if version != _VERSION:
            raise ValueError(f"Unsupported wire format version: {version}")

        nonce = ciphertext[1:1 + _NONCE_BYTES]
        ct = ciphertext[1 + _NONCE_BYTES:]

        return self._aesgcm.decrypt(nonce, ct, associated_data)

    def encrypt_str(self, text: str, associated_data: Optional[bytes] = None) -> str:
        """Encrypt a string, return hex-encoded ciphertext."""
        raw = self.encrypt(text, associated_data)
        return raw.hex()

    def decrypt_str(self, hex_ct: str, associated_data: Optional[bytes] = None) -> str:
        """Decrypt hex-encoded ciphertext, return string."""
        raw = self.decrypt(bytes.fromhex(hex_ct), associated_data)
        return raw.decode("utf-8")

    # ── Utilities ─────────────────────────────────────────────────────

    @staticmethod
    def key_fingerprint(key: bytes) -> str:
        """SHA-256 fingerprint of a key (first 12 hex chars)."""
        return hashlib.sha256(key).hexdigest()[:12]

    def __repr__(self) -> str:
        fp = self.key_fingerprint(self._key)
        return f"SynapseCrypto(fingerprint={fp})"
