"""
Synapse Layer — LangChain Integration Example

Demonstrates how to use Synapse Layer as persistent memory
for a LangChain conversational agent.

Requirements:
    pip install synapse-layer langchain-core

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import asyncio
from synapse_memory.integrations import SynapseChatMessageHistory


async def main():
    # Initialize Synapse Layer as your LangChain message history
    history = SynapseChatMessageHistory(
        agent_id="demo-agent",
        session_id="onboarding-session",
    )

    # Store conversation messages
    # Each message passes through the Cognitive Security pipeline:
    # PII redaction → Intent validation → AES-256 encryption
    history.add_user_message("I prefer concise, technical responses.")
    history.add_ai_message("Noted — I'll keep responses brief and precise.")
    history.add_user_message("My project deadline is next Friday.")
    history.add_ai_message("I'll factor that deadline into my suggestions.")

    print("Stored 4 messages through Synapse Layer.")
    print(f"Memories in vault: {len(history._memory._memories)}")
    print()

    # Retrieve messages in LangChain-compatible format
    messages = await history.aget_messages()
    print(f"Retrieved {len(messages)} messages:")
    for msg in messages:
        role = "User" if msg.type == "human" else "AI"
        print(f"  [{role}] {msg.content}")
    print()

    # Use with RunnableWithMessageHistory (LangChain LCEL):
    #
    # from langchain_core.runnables.history import RunnableWithMessageHistory
    #
    # chain_with_history = RunnableWithMessageHistory(
    #     runnable=your_chain,
    #     get_session_history=lambda session_id: SynapseChatMessageHistory(
    #         agent_id="your-agent",
    #         session_id=session_id,
    #     ),
    # )
    #
    # response = chain_with_history.invoke(
    #     {"input": "What were my preferences?"},
    #     config={"configurable": {"session_id": "user-123"}},
    # )

    print("Done. Memory persists across sessions with encrypted persistent memory.")


if __name__ == "__main__":
    asyncio.run(main())
