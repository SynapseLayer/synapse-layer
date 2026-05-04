"""
Synapse Layer — CrewAI Integration Example

Demonstrates how to use Synapse Layer as the persistent memory
backend for a CrewAI crew.

Requirements:
    pip install synapse-layer crewai

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from synapse_memory.integrations.crewai_memory import SynapseCrewStorage


def main():
    # Initialize Synapse Layer as CrewAI's memory storage backend.
    # Every memory passes through the Cognitive Security pipeline:
    # PII redaction → Intent validation → AES-256 encryption
    storage = SynapseCrewStorage(agent_id="research-crew")

    # Use with CrewAI's Memory system:
    #
    # from crewai import Agent, Crew, Task
    # from crewai.memory.unified_memory import Memory
    #
    # memory = Memory(storage=storage)
    #
    # researcher = Agent(
    #     role="Senior Researcher",
    #     goal="Find and summarize key insights",
    #     backstory="Expert analyst with deep domain knowledge.",
    # )
    #
    # task = Task(
    #     description="Research the latest trends in AI agent memory.",
    #     expected_output="A summary of key trends.",
    #     agent=researcher,
    # )
    #
    # crew = Crew(
    #     agents=[researcher],
    #     tasks=[task],
    #     memory=memory,  # Synapse Layer handles persistence
    # )
    #
    # result = crew.kickoff()

    # --- Standalone demo (no LLM required) ---

    from crewai.memory.types import MemoryRecord

    # Store memories through the Synapse security pipeline
    records = [
        MemoryRecord(
            content="User prefers concise technical reports.",
            scope="/crew/research",
            categories=["preference"],
            importance=0.8,
        ),
        MemoryRecord(
            content="Project deadline is April 15, 2026.",
            scope="/crew/research",
            categories=["deadline", "project"],
            importance=0.9,
        ),
    ]
    storage.save(records)
    print(f"Stored {len(records)} records through Synapse Layer.")
    print(f"Total memories in vault: {storage.count()}")
    print()

    # List records back
    stored = storage.list_records(scope_prefix="/crew/research")
    for rec in stored:
        print(f"  [{rec.importance:.1f}] {rec.content}")
    print()

    # Scope info
    info = storage.get_scope_info("/crew/research")
    print(f"Scope: {info.path}")
    print(f"  Records: {info.record_count}")
    print(f"  Categories: {info.categories}")
    print()

    print("Done. Memory persists across sessions with encrypted persistent memory.")


if __name__ == "__main__":
    main()
