"""
Cryptographic Operations — AES-256-GCM, PBKDF2

Provides at-rest encryption for memory content using
industry-standard AES-256-GCM with PBKDF2 key derivation.

Usage::

    from synapse_memory.crypto import SynapseCrypto

    crypto = SynapseCrypto.from_password("my-secret")
    ct = crypto.encrypt(b"sensitive data")
    pt = crypto.decrypt(ct)

    # Or with raw 32-byte key
    key = SynapseCrypto.generate_key()
    crypto = SynapseCrypto(key)

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from .aes import SynapseCrypto

__all__ = ["SynapseCrypto"]
