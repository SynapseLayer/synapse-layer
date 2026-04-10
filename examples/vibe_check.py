#!/usr/bin/env python3
"""vibe_check.py — Synapse Layer in 30 seconds.

Run:
    pip install synapse-layer
    python vibe_check.py

What happens:
    1. Creates a local memory vault (SQLite, zero-config)
    2. Stores a memory through the full Cognitive Security Pipeline
    3. Recalls it deterministically with Trust Quotient scoring
    4. Uses @remember to auto-inject memory into any function

No API keys. No cloud. No config. Just memory that persists.
"""
import asyncio
from synapse_memory import SynapseMemory, SqliteBackend, remember


async def main():
    # ━━━ 1. Create memory vault ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    memory = SynapseMemory(
        agent_id="vibe-agent",
        backend=SqliteBackend("vibe_check.db"),
    )
    print("🧠 Synapse Layer — Vibe Check")
    print("=" * 42)

    # ━━━ 2. Store through Cognitive Security Pipeline ━━━━━━━━
    result = await memory.store(
        content="User loves Python, hates boilerplate, builds AI agents for a living",
        confidence=0.95,
    )
    print(f"\n✅ Memory stored")
    print(f"   Trust Quotient : {result.trust_quotient:.2f}")
    print(f"   PII sanitized  : {result.sanitized}")
    print(f"   Privacy applied : {result.privacy_applied}")
    print(f"   Intent category : {result.intent_category}")

    # ━━━ 3. Deterministic recall ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    recalls = await memory.recall("what does the user do?")
    print(f"\n🔍 Recall results ({len(recalls)} memories):")
    for r in recalls:
        print(f"   → {r.content[:60]}... (TQ: {r.trust_quotient:.2f})")

    # ━━━ 4. @remember — the killer feature ━━━━━━━━━━━━━━━━━━━
    @remember(memory)
    async def answer(prompt: str) -> str:
        """This function auto-recalls + auto-stores every call."""
        return f"[LLM would respond to: {prompt}]"

    response = await answer("What are the user's preferences?")
    print(f"\n🔮 @remember response:")
    print(f"   {response}")

    # ━━━ 5. Verify persistence ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    total = await memory.recall("*")
    print(f"\n📦 Total memories in vault: {len(total)}")
    print(f"\n✨ Vibe check passed. Your agent has a past now.")
    print(f"   DB file: vibe_check.db (portable, encrypted, yours)")


if __name__ == "__main__":
    asyncio.run(main())
