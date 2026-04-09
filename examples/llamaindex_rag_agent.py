"""
Synapse Layer — LlamaIndex Integration Example

Demonstrates how to use Synapse Layer as:
1. A retriever for RAG pipelines (SynapseRetriever)
2. A persistent chat store (SynapseChatStore)

Requirements:
    pip install synapse-layer[llamaindex]

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio

from synapse_memory.integrations.llamaindex import (
    SynapseRetriever,
    SynapseChatStore,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole


async def retriever_demo():
    """Demonstrate the SynapseRetriever."""
    print("=" * 60)
    print("SynapseRetriever Demo")
    print("=" * 60)

    retriever = SynapseRetriever(agent_id="demo-retriever", top_k=3)
    print(f"Initialized: {retriever}")

    # Populate the memory store
    await retriever.astore("Our deployment strategy uses blue-green on Kubernetes.")
    await retriever.astore("The primary database is PostgreSQL 16 on AWS RDS.")
    await retriever.astore("API rate limit is 1000 requests per minute per client.")
    print("Stored 3 knowledge entries.\n")

    # Retrieve relevant nodes
    from llama_index.core.schema import QueryBundle
    query = QueryBundle(query_str="What is our deployment strategy?")
    nodes = await retriever._aretrieve(query)

    print(f"Query: '{query.query_str}'")
    for nws in nodes:
        tq = nws.score
        print(f"  [{tq:.2f}] {nws.node.text}")

    # In a real LlamaIndex application:
    #
    #   from llama_index.core import VectorStoreIndex
    #   index = VectorStoreIndex.from_documents(documents)
    #   query_engine = index.as_query_engine(retriever=retriever)
    #   response = query_engine.query("What is our deployment strategy?")


async def chat_store_demo():
    """Demonstrate the SynapseChatStore."""
    print("\n" + "=" * 60)
    print("SynapseChatStore Demo")
    print("=" * 60)

    store = SynapseChatStore(agent_id="demo-chat")
    print(f"Initialized: {store}")

    # Add messages to a conversation
    store.add_message("session-1", ChatMessage(
        role=MessageRole.USER,
        content="What databases do we support?",
    ))
    store.add_message("session-1", ChatMessage(
        role=MessageRole.ASSISTANT,
        content="We support PostgreSQL, MySQL, and SQLite.",
    ))
    store.add_message("session-1", ChatMessage(
        role=MessageRole.USER,
        content="Which one is recommended for production?",
    ))
    print("Added 3 messages to session-1.\n")

    # Retrieve conversation
    messages = store.get_messages("session-1")
    for msg in messages:
        print(f"  [{msg.role.value}] {msg.content}")

    # List keys
    print(f"\nActive sessions: {store.get_keys()}")

    # In a real LlamaIndex application:
    #
    #   from llama_index.core.memory import ChatMemoryBuffer
    #   memory = ChatMemoryBuffer.from_defaults(
    #       chat_store=store,
    #       chat_store_key="session-1",
    #   )


async def main():
    await retriever_demo()
    await chat_store_demo()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
