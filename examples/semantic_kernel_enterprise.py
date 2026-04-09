"""
Synapse Layer — Semantic Kernel Integration Example

Demonstrates how to use Synapse Layer as:
1. A persistent, encrypted chat history (SynapseChatHistory)
2. A memory store for knowledge retrieval (SynapseMemoryStore)

Requirements:
    pip install synapse-layer[semantic-kernel]

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
import numpy as np

from synapse_memory.integrations.semantic_kernel import (
    SynapseChatHistory,
    SynapseMemoryStore,
)
from semantic_kernel.memory.memory_record import MemoryRecord


async def chat_history_demo():
    """Demonstrate SynapseChatHistory."""
    print("=" * 60)
    print("SynapseChatHistory Demo")
    print("=" * 60)

    history = SynapseChatHistory(agent_id="demo-copilot")
    print(f"Initialized: {history}")

    # Add messages — each is automatically persisted through
    # the Cognitive Security pipeline (PII redaction + AES-256)
    history.add_system_message("You are a helpful enterprise assistant.")
    history.add_user_message("What is our Q4 revenue target?")
    history.add_assistant_message("The Q4 revenue target is $12.5M.")
    print(f"\nMessages stored: {len(history)}")

    for msg in history.messages:
        print(f"  [{msg.role.value}] {msg.content}")

    # In a real Semantic Kernel application:
    #
    #   from semantic_kernel import Kernel
    #   kernel = Kernel()
    #   # ... add chat service ...
    #   result = await kernel.invoke(
    #       function, chat_history=history
    #   )


async def memory_store_demo():
    """Demonstrate SynapseMemoryStore."""
    print("\n" + "=" * 60)
    print("SynapseMemoryStore Demo")
    print("=" * 60)

    store = SynapseMemoryStore(agent_id="demo-enterprise")
    print(f"Initialized: {store}")

    # Create a collection
    await store.create_collection("company-knowledge")
    print(f"Collections: {await store.get_collections()}")

    # Upsert records
    records = [
        MemoryRecord.local_record(
            id="rec-1",
            text="Our deployment uses blue-green strategy on Kubernetes.",
            description="Deployment strategy",
            additional_metadata='{"team": "platform"}',
            embedding=np.random.rand(3),
        ),
        MemoryRecord.local_record(
            id="rec-2",
            text="The primary database is PostgreSQL 16 on AWS RDS.",
            description="Database infrastructure",
            additional_metadata='{"team": "data"}',
            embedding=np.random.rand(3),
        ),
    ]
    ids = await store.upsert_batch("company-knowledge", records)
    print(f"Upserted: {ids}")

    # Retrieve a record
    rec = await store.get("company-knowledge", "rec-1", with_embedding=False)
    print(f"\nRetrieved: id={rec.id}, text={rec.text}")

    # In a real application, SemanticTextMemory would handle
    # the embedding generation and nearest-match queries:
    #
    #   from semantic_kernel.memory import SemanticTextMemory
    #   memory = SemanticTextMemory(storage=store, embeddings_generator=embedder)
    #   result = await memory.search("company-knowledge", "deployment", limit=3)

    print("\nDone.")


async def main():
    await chat_history_demo()
    await memory_store_demo()


if __name__ == "__main__":
    asyncio.run(main())
