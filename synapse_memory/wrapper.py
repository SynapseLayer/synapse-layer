"""
Synapse Layer — ``remember`` Wrapper

Drop-in decorator that adds automatic recall-before + store-after
semantics to any async function.  Perfect for agent tool functions.

Usage::

    from synapse_memory import SynapseMemory
    from synapse_memory.wrapper import remember

    memory = SynapseMemory(agent_id="my-agent")

    @remember(memory, auto_store=True, top_k=3)
    async def answer(prompt: str) -> str:
        # `prompt` is enriched with recalled context
        return f"Answering: {prompt}"

    result = await answer("What color does the user prefer?")
    # 1. Recalls relevant memories for the prompt
    # 2. Injects context into the first string argument
    # 3. Calls the wrapped function
    # 4. Stores the result as a new memory

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import functools
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar, Union

from .core import SynapseMemory

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def remember(
    memory: SynapseMemory,
    *,
    auto_store: bool = True,
    top_k: int = 3,
    confidence: float = 0.85,
    context_prefix: str = "\n\n[Recalled context]:\n",
    inject_context: bool = True,
) -> Callable[[F], F]:
    """Decorator that wraps a function with recall-before + store-after.

    Args:
        memory: SynapseMemory instance to use.
        auto_store: If True, stores the function return value.
        top_k: Number of memories to recall.
        confidence: Confidence for stored memories.
        context_prefix: Prefix for injected context.
        inject_context: If True, appends recalled context to first str arg.

    Returns:
        Decorated function with memory semantics.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # ── Phase 1: Recall ───────────────────────────────────
            query = _extract_query(args, kwargs, fn)
            recalled = []
            if query:
                try:
                    recalled = await memory.recall(query, top_k=top_k)
                    logger.debug(
                        "remember: recalled %d memories for '%s'",
                        len(recalled), query[:50],
                    )
                except Exception as exc:
                    logger.warning("remember: recall failed: %s", exc)

            # ── Phase 2: Inject context ───────────────────────────
            if inject_context and recalled and args:
                enriched_args = list(args)
                for i, a in enumerate(enriched_args):
                    if isinstance(a, str):
                        context_block = context_prefix + "\n".join(
                            f"- {r.content}" for r in recalled
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
                        await memory.store(
                            content=content,
                            confidence=confidence,
                            metadata={"source": f"remember:{fn.__name__}"},
                        )
                        logger.debug(
                            "remember: stored result from %s (%d chars)",
                            fn.__name__, len(content),
                        )
                    except Exception as exc:
                        logger.warning("remember: store failed: %s", exc)

            return result

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            import asyncio
            return asyncio.get_event_loop().run_until_complete(
                async_wrapper(*args, **kwargs)
            )

        if inspect.iscoroutinefunction(fn):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _extract_query(
    args: tuple, kwargs: dict, fn: Callable
) -> Optional[str]:
    """Extract the recall query from function arguments.

    Strategy: first positional str arg, or first str kwarg.
    """
    for a in args:
        if isinstance(a, str) and a.strip():
            return a
    for v in kwargs.values():
        if isinstance(v, str) and v.strip():
            return v
    return None
