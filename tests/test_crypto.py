"""Tests for SynapseCrypto — AES-256-GCM encryption."""

import os
import pytest

from synapse_memory.crypto import SynapseCrypto


@pytest.fixture
def crypto():
    key = SynapseCrypto.generate_key()
    return SynapseCrypto(key)


class TestKeyGeneration:
    def test_key_length(self):
        key = SynapseCrypto.generate_key()
        assert len(key) == 32

    def test_keys_are_unique(self):
        k1 = SynapseCrypto.generate_key()
        k2 = SynapseCrypto.generate_key()
        assert k1 != k2

    def test_invalid_key_length(self):
        with pytest.raises(ValueError):
            SynapseCrypto(b"short")

    def test_invalid_key_type(self):
        with pytest.raises(ValueError):
            SynapseCrypto("not bytes")  # type: ignore


class TestEncryptDecrypt:
    def test_roundtrip_bytes(self, crypto):
        pt = b"User prefers dark mode"
        ct = crypto.encrypt(pt)
        assert crypto.decrypt(ct) == pt

    def test_roundtrip_str(self, crypto):
        pt = "Usu\u00e1rio prefere modo escuro"
        ct = crypto.encrypt(pt)
        assert crypto.decrypt(ct).decode("utf-8") == pt

    def test_roundtrip_str_helpers(self, crypto):
        pt = "Hello Synapse"
        hex_ct = crypto.encrypt_str(pt)
        assert isinstance(hex_ct, str)
        assert crypto.decrypt_str(hex_ct) == pt

    def test_different_nonces(self, crypto):
        pt = b"same plaintext"
        ct1 = crypto.encrypt(pt)
        ct2 = crypto.encrypt(pt)
        assert ct1 != ct2  # Different nonces

    def test_associated_data(self, crypto):
        pt = b"secret"
        aad = b"agent_id:test-agent"
        ct = crypto.encrypt(pt, associated_data=aad)
        assert crypto.decrypt(ct, associated_data=aad) == pt

    def test_wrong_aad_fails(self, crypto):
        pt = b"secret"
        ct = crypto.encrypt(pt, associated_data=b"correct")
        with pytest.raises(Exception):  # InvalidTag
            crypto.decrypt(ct, associated_data=b"wrong")

    def test_tampered_ciphertext_fails(self, crypto):
        ct = crypto.encrypt(b"data")
        tampered = ct[:-1] + bytes([ct[-1] ^ 0xFF])
        with pytest.raises(Exception):
            crypto.decrypt(tampered)

    def test_too_short_ciphertext(self, crypto):
        with pytest.raises(ValueError, match="too short"):
            crypto.decrypt(b"\x01" + b"\x00" * 5)

    def test_wrong_version(self, crypto):
        ct = crypto.encrypt(b"data")
        bad = bytes([0xFF]) + ct[1:]
        with pytest.raises(ValueError, match="version"):
            crypto.decrypt(bad)

    def test_wrong_key_fails(self):
        c1 = SynapseCrypto(SynapseCrypto.generate_key())
        c2 = SynapseCrypto(SynapseCrypto.generate_key())
        ct = c1.encrypt(b"secret")
        with pytest.raises(Exception):
            c2.decrypt(ct)


class TestPasswordDerivation:
    def test_from_password(self):
        crypto = SynapseCrypto.from_password("my-secret", salt=b"0" * 16)
        pt = b"test data"
        ct = crypto.encrypt(pt)
        assert crypto.decrypt(ct) == pt

    def test_same_password_same_salt(self):
        salt = os.urandom(16)
        c1 = SynapseCrypto.from_password("pass", salt=salt)
        c2 = SynapseCrypto.from_password("pass", salt=salt)
        ct = c1.encrypt(b"data")
        assert c2.decrypt(ct) == b"data"

    def test_different_salt_different_key(self):
        c1 = SynapseCrypto.from_password("pass", salt=b"a" * 16)
        c2 = SynapseCrypto.from_password("pass", salt=b"b" * 16)
        ct = c1.encrypt(b"data")
        with pytest.raises(Exception):
            c2.decrypt(ct)


class TestEnvFactory:
    def test_from_env(self, monkeypatch):
        key = SynapseCrypto.generate_key()
        monkeypatch.setenv("SYNAPSE_ENCRYPTION_KEY", key.hex())
        crypto = SynapseCrypto.from_env()
        assert crypto is not None
        ct = crypto.encrypt(b"via env")
        assert crypto.decrypt(ct) == b"via env"

    def test_from_env_missing(self, monkeypatch):
        monkeypatch.delenv("SYNAPSE_ENCRYPTION_KEY", raising=False)
        assert SynapseCrypto.from_env() is None

    def test_from_env_custom_var(self, monkeypatch):
        key = SynapseCrypto.generate_key()
        monkeypatch.setenv("MY_KEY", key.hex())
        crypto = SynapseCrypto.from_env("MY_KEY")
        assert crypto is not None


class TestUtilities:
    def test_fingerprint(self):
        key = SynapseCrypto.generate_key()
        fp = SynapseCrypto.key_fingerprint(key)
        assert len(fp) == 12
        assert all(c in "0123456789abcdef" for c in fp)

    def test_repr(self, crypto):
        r = repr(crypto)
        assert "SynapseCrypto" in r
        assert "fingerprint=" in r
