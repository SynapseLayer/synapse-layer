"""
Tests for the secure-memory MCP reference server ``health_check`` tool.

Production incident context
---------------------------
The hosted ``health_check`` probe was returning 5XX with
``"Plaintext recall requires token scope 'read:fulltext' or 'admin:export'"``
because the health probe was wired to a high-privilege recall path. These
tests lock in the correct contract for the reference implementation:

  * ``health_check`` is a PURE, low-privilege status probe.
  * It MUST NEVER call ``recall`` / ``search`` / ``store`` (i.e. never touch
    an operation requiring ``read:fulltext`` or ``admin:export`` scope).
  * It MUST NEVER expose plaintext memory content in its response.

The MCP ``FastMCP`` decorator is stubbed so these tests exercise the tool
logic directly and stay independent of the installed ``mcp`` package version.
All fixture data uses the ``__test_`` prefix.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

SERVER_PATH = (
    Path(__file__).resolve().parent.parent
    / "examples"
    / "mcp-secure-memory"
    / "server.py"
)


def _install_fastmcp_stub() -> None:
    """Inject a no-op FastMCP into sys.modules so importing the reference
    server does not require a specific ``mcp`` package version.

    The stub's ``tool()`` returns the undecorated function unchanged, so each
    tool remains a plain callable we can invoke directly.
    """
    mcp_mod = types.ModuleType("mcp")
    server_mod = types.ModuleType("mcp.server")
    fastmcp_mod = types.ModuleType("mcp.server.fastmcp")

    class _StubFastMCP:
        def __init__(self, *args, **kwargs) -> None:
            self._name = args[0] if args else "stub"

        def tool(self, *dargs, **dkwargs):
            def _decorator(fn):
                return fn  # register as no-op, return original callable

            return _decorator

        def run(self, *args, **kwargs) -> None:  # pragma: no cover - entrypoint
            return None

    fastmcp_mod.FastMCP = _StubFastMCP
    server_mod.fastmcp = fastmcp_mod
    mcp_mod.server = server_mod
    sys.modules["mcp"] = mcp_mod
    sys.modules["mcp.server"] = server_mod
    sys.modules["mcp.server.fastmcp"] = fastmcp_mod


def _load_server():
    _install_fastmcp_stub()
    spec = importlib.util.spec_from_file_location(
        "synapse_mcp_secure_memory_server", SERVER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def server():
    return _load_server()


def test_health_check_returns_healthy_status(server) -> None:
    """A valid low-privilege probe returns a healthy status envelope
    (the analogue of an HTTP 200) with non-sensitive metadata only."""
    result = server.health_check()

    assert result["status"] == "healthy"
    assert result["version"]  # SDK version populated
    assert result["engine"] == "synapse-layer"
    assert "timestamp" in result and result["timestamp"]
    # Backend is reported by class name only — never contents.
    assert result["backend"] == "MemoryBackend"
    assert set(result["capabilities"]) == {"sanitize", "privacy"}


def test_health_check_never_calls_recall_or_store(server) -> None:
    """health_check MUST NOT invoke any high-privilege data operation.

    We booby-trap recall/store/search so that ANY call fails the test. A
    passing run proves the probe never touches a ``read:fulltext`` /
    ``admin:export`` scoped path.
    """

    def _boom(*args, **kwargs):  # pragma: no cover - must never run
        raise AssertionError(
            "health_check invoked a high-privilege operation "
            "(recall/store/search) — scope violation!"
        )

    server.memory.recall = _boom
    server.memory.store = _boom
    if hasattr(server.memory, "search"):
        server.memory.search = _boom

    result = server.health_check()  # must not raise
    assert result["status"] == "healthy"


def test_health_check_no_plaintext_exposure(server) -> None:
    """Even with data present, health_check must expose zero plaintext."""
    canary = "__test_TOPSECRET_CANARY_98765"

    # Seed a record directly into the in-memory backup list so we do not
    # rely on a high-privilege write path. This mimics stored plaintext.
    server.memory._memories.append(
        {"content": canary, "metadata": {"tag": "__test_seed"}}
    )

    result = server.health_check()
    serialized = json.dumps(result)

    assert canary not in serialized, (
        "PLAINTEXT LEAK: stored memory content appeared in health_check output"
    )
    # Defensive: no obvious content field is echoed back.
    assert "content" not in result
