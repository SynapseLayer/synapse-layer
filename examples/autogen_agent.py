"""
Synapse Layer — AutoGen Integration Example

Demonstrates how to use Synapse Layer as persistent memory
for an AutoGen agent.

Requirements:
    pip install synapse-layer 'autogen-agentchat>=0.7' 'autogen-core>=0.7'

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio

from autogen_core.memory import MemoryContent, MemoryMimeType
from synapse_memory.integrations import SynapseAutoGenMemory


async def main():
    # Initialize Synapse Layer as your AutoGen memory backend
    memory = SynapseAutoGenMemory(
        agent_id="demo-autogen-agent",
        top_k=3,
    )
    print(f"Initialized: {memory}")

    # Store some memories
    await memory.add(MemoryContent(
        content="The project deadline is March 15, 2026.",
        mime_type=MemoryMimeType.TEXT,
    ))
    await memory.add(MemoryContent(
        content="Use PostgreSQL for the production database.",
        mime_type=MemoryMimeType.TEXT,
    ))
    await memory.add(MemoryContent(
        content="The API rate limit is 1000 requests per minute.",
        mime_type=MemoryMimeType.TEXT,
    ))
    print("Stored 3 memories.")

    # Query memories
    result = await memory.query("What is the project deadline?")
    print(f"\nQuery: 'What is the project deadline?'")
    for r in result.results:
        tq = r.metadata.get("trust_quotient", 0) if r.metadata else 0
        print(f"  [{tq:.2f}] {r.content}")

    # In a real AutoGen application, you would pass the memory
    # to an AssistantAgent:
    #
    #   from autogen_agentchat.agents import AssistantAgent
    #   from autogen_ext.models.openai import OpenAIChatCompletionClient
    #
    #   client = OpenAIChatCompletionClient(model="gpt-4o")
    #   agent = AssistantAgent(
    #       name="assistant",
    #       model_client=client,
    #       memory=[memory],
    #   )
    #
    # The agent will automatically call memory.update_context()
    # before each LLM invocation, injecting relevant memories.

    # Cleanup
    await memory.clear()
    await memory.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
