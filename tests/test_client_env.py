"""Env-var precedence tests for the Synapse HTTP client token resolution.

Covers CID SL-SDK-ENV-20260916-v1.0: X_CONNECT_TOKEN is the canonical env,
SYNAPSE_TOKEN is a silent compat fallback, and explicit kwargs always win.

No network is performed: the httpx client is created lazily in
``_get_client``; ``__init__`` only resolves and validates the token string.

License: Apache 2.0
"""

import os
from unittest.mock import patch

from synapse_memory.client import Synapse

# Dummy sk_connect_* values (never real secrets) — required by prefix validation.
_KW = "sk_connect_KWARG_dummy"
_XCONNECT = "sk_connect_XCONNECT_dummy"
_LEGACY = "sk_connect_LEGACY_dummy"


def test_kwarg_beats_env():
    """Explicit api_key kwarg wins over both env vars."""
    with patch.dict(os.environ, {"X_CONNECT_TOKEN": _XCONNECT, "SYNAPSE_TOKEN": _LEGACY}):
        c = Synapse(_KW)
        assert c._api_key == _KW


def test_token_kwarg_beats_env():
    """Explicit token kwarg wins over both env vars."""
    with patch.dict(os.environ, {"X_CONNECT_TOKEN": _XCONNECT, "SYNAPSE_TOKEN": _LEGACY}):
        c = Synapse(token=_KW)
        assert c._api_key == _KW


def test_xconnect_beats_synapse_token():
    """X_CONNECT_TOKEN (canonical) is read before SYNAPSE_TOKEN (legacy)."""
    with patch.dict(os.environ, {"X_CONNECT_TOKEN": _XCONNECT, "SYNAPSE_TOKEN": _LEGACY}):
        c = Synapse()
        assert c._api_key == _XCONNECT


def test_synapse_token_fallback_when_xconnect_absent():
    """SYNAPSE_TOKEN still works as a fallback when X_CONNECT_TOKEN is unset."""
    env = {k: v for k, v in os.environ.items() if k not in ("X_CONNECT_TOKEN",)}
    env["SYNAPSE_TOKEN"] = _LEGACY
    with patch.dict(os.environ, env, clear=True):
        c = Synapse()
        assert c._api_key == _LEGACY
