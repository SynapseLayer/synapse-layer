"""
Synapse Layer — ``remember`` Wrapper

Drop-in decorator that adds automatic recall-before + store-after
semantics to any function. Works with both local SynapseMemory and
remote Forge API via token.

Usage with token (recommended — Forge API)::

    from synapse_layer import remember

    @remember(token="sk_connect_xxx", agent_id="my-agent")
    def agent(input: str) -> str:
        return llm.generate(input)

Usage with SynapseMemory (local)::

    from synapse_memory import SynapseMemory
    from synapse_memory.wrapper import remember

    memory = SynapseMemory(agent_id="my-agent")

    @remember(memory, auto_store=True, top_k=3)
    async def answer(prompt: str) -> str:
        return f"Answering: {prompt}"

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def remember(
    memory_or_token: Any = None,
    *,
    token: Optional[str] = None,
    agent_id: str = "default",
    auto_store: bool = True,
    top_k: int = 3,
    confidence: float = 0.85,
    context_prefix: str = "\n\n[Recalled context]:\n",
    inject_context: bool = True,
    verbose: bool = False,
) -> Callable[[F], F]:
    """Decorator that wraps a function with recall-before + store-after.

    Can be used in two modes:

    1. **Token mode** (Forge API)::

        @remember(token="sk_connect_xxx")
        def my_agent(input: str) -> str: ...

    2. **Memory mode** (local SynapseMemory)::

        memory = SynapseMemory(agent_id="x")
        @remember(memory)
        async def my_agent(prompt: str) -> str: ...

    Args:
        memory_or_token: SynapseMemory instance OR sk_connect token string.
        token: Explicit token (keyword). Takes precedence.
        agent_id: Agent identifier (token mode only).
        auto_store: If True, stores the function return value.
        top_k: Number of memories to recall.
        confidence: Confidence for stored memories.
        context_prefix: Prefix for injected context.
        inject_context: If True, appends recalled context to first str arg.
        verbose: Enable verbose logging.

    Returns:
        Decorated function with memory semantics.
    """
    # Determine mode
    resolved_token = token
    memory_instance = None

    if isinstance(memory_or_token, str) and memory_or_token.startswith("sk_connect_"):
        resolved_token = memory_or_token
    elif memory_or_token is not None and not isinstance(memory_or_token, str):
        # Assume it's a SynapseMemory instance
        memory_instance = memory_or_token

    def _log(*args: Any) -> None:
        if verbose:
            print("[Synapse]", *args)

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _get_client()
            query = _extract_query(args, kwargs, fn)
            recalled = []

            # ── Phase 1: Recall ───────────────────────────────────
            if query:
                try:
                    recalled = await _async_recall(client, query, top_k)
                    _log(f"Recalling... {len(recalled)} memories {'(first run)' if not recalled else 'found'}")
                    if recalled:
                        for r in recalled:
                            c = r if isinstance(r, str) else (r.get("content", "") if isinstance(r, dict) else getattr(r, "content", str(r)))
                            _log(f'Context injected: "{c[:60]}"')
                except Exception as exc:
                    _log(f"Recall failed: {exc}")

            # ── Phase 2: Inject context ───────────────────────────
            if inject_context and recalled and args:
                enriched_args = list(args)
                for i, a in enumerate(enriched_args):
                    if isinstance(a, str):
                        context_block = context_prefix + "\n".join(
                            _content_str(r) for r in recalled
                        )
                        enriched_args[i] = a + context_block
                        break
                args = tuple(enriched_args)

            # ── Phase 3: Execute ─────────────────────────────────
            result = await fn(*args, **kwargs)

            # ── Phase 4: Store ───────────────────────────────────
            if auto_store and result is not None:
                content = str(result) if not isinstance(result, str) else result
                if content.strip():
                    try:
                        save_result = await _async_store(client, content, confidence, fn.__name__)
                        _log(f"Memory saved: id={_get_id(save_result)}")
                    except Exception as exc:
                        _log(f"Store failed: {exc}")

            return result

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            client = _get_client()
            query = _extract_query(args, kwargs, fn)
            recalled = []

            # ── Phase 1: Recall ───────────────────────────────────
            if query:
                try:
                    recalled = _sync_recall(client, query, top_k)
                    _log(f"Recalling... {len(recalled)} memories {'(first run)' if not recalled else 'found'}")
                    if recalled:
                        for r in recalled:
                            c = _content_str(r)
                            _log(f'Context injected: "{c[:60]}"')
                except Exception as exc:
                    _log(f"Recall failed: {exc}")

            # ── Phase 2: Inject context ───────────────────────────
            if inject_context and recalled and args:
                enriched_args = list(args)
                for i, a in enumerate(enriched_args):
                    if isinstance(a, str):
                        context_block = context_prefix + "\n".join(
                            f"- {_content_str(r)}" for r in recalled
                        )
                        enriched_args[i] = a + context_block
                        break
                args = tuple(enriched_args)

            # ── Phase 3: Execute ─────────────────────────────────
            result = fn(*args, **kwargs)

            # ── Phase 4: Store ───────────────────────────────────
            if auto_store and result is not None:
                content = str(result) if not isinstance(result, str) else result
                if content.strip():
                    try:
                        save_result = _sync_store(client, content, confidence, fn.__name__)
                        _log(f"Memory saved: id={_get_id(save_result)}")
                    except Exception as exc:
                        _log(f"Store failed: {exc}")

            return result

        def _get_client() -> Any:
            if memory_instance is not None:
                return memory_instance
            if resolved_token:
                from .client import Synapse
                return Synapse(token=resolved_token, agent_id=agent_id, verbose=verbose)
            raise ValueError("remember() requires either a token or SynapseMemory instance")

        _log(f"@remember active for agent: {agent_id}")

        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


# ── Internal helpers ─────────────────────────────────────────────────

def _content_str(r: Any) -> str:
    if isinstance(r, str):
        return r
    if isinstance(r, dict):
        return r.get("content", str(r))
    return getattr(r, "content", str(r))


def _get_id(r: Any) -> str:
    if isinstance(r, dict):
        return r.get("memoryId", r.get("id", "?"))
    return getattr(r, "memoryId", getattr(r, "id", "?"))


def _sync_recall(client: Any, query: str, top_k: int) -> list:
    if hasattr(client, "recall") and callable(client.recall):
        result = client.recall(query, top_k=top_k)
        if isinstance(result, list):
            return result
        # SynapseMemory.recall returns list of RecallResult
        return result if result else []
    return []


def _sync_store(client: Any, content: str, confidence: float, fn_name: str) -> Any:
    if hasattr(client, "remember") and callable(client.remember):
        return client.remember(content, metadata={"source": f"remember:{fn_name}"})
    if hasattr(client, "store") and callable(client.store):
        return client.store(content)
    return None


async def _async_recall(client: Any, query: str, top_k: int) -> list:
    recall_fn = getattr(client, "recall", None)
    if recall_fn is None:
        return []
    if inspect.iscoroutinefunction(recall_fn):
        result = await recall_fn(query, top_k=top_k)
    else:
        result = recall_fn(query, top_k=top_k)
    return result if isinstance(result, list) else (result or [])


async def _async_store(client: Any, content: str, confidence: float, fn_name: str) -> Any:
    store_fn = getattr(client, "remember", getattr(client, "store", None))
    if store_fn is None:
        return None
    if inspect.iscoroutinefunction(store_fn):
        return await store_fn(content)
    return store_fn(content)


def _extract_query(
    args: tuple, kwargs: dict, fn: Callable
) -> Optional[str]:
    """Extract the recall query from function arguments."""
    for a in args:
        if isinstance(a, str) and a.strip():
            return a
    for v in kwargs.values():
        if isinstance(v, str) and v.strip():
            return v
    return None
