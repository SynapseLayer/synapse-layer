"""
Synapse Layer — Auto-Save Engine Demo

Demonstrates how to use the AutoSaveEngine for autonomous memory
persistence. Shows three usage patterns:
  1. Direct event creation and save
  2. Automatic trigger detection via process_text()
  3. Integration with MCP tools

Requirements:
    pip install synapse-layer
    # Configure: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from synapse_memory.autosave import (
    AutoSaveEngine,
    AutoSaveEvent,
    PolicyEngine,
    TriggerDetector,
    EventFormatter,
)


def demo_event_creation():
    """Pattern 1: Create and save events explicitly."""
    print("\n" + "=" * 60)
    print("Pattern 1: Explicit Event Creation")
    print("=" * 60)

    event = AutoSaveEvent(
        content="Decided to pivot OFFLY to B2B SaaS model",
        project="OFFLY",
        type="[DECISION]",
        importance=4,
        source="chatllm_teams",
        tags=["pivot", "b2b", "strategy"],
        source_ref={"conversation_id": "abc-123"},
    )

    print(f"  Event: {event.type} / {event.project}")
    print(f"  Importance: {event.importance}")
    print(f"  Tags: {event.tags}")

    # In production, you'd pass this to engine.save(event)
    # result = engine.save(event)
    # print(f"  Result: {result.status} (id={result.id})")


def demo_trigger_detection():
    """Pattern 2: Auto-detect triggers in free text."""
    print("\n" + "=" * 60)
    print("Pattern 2: Automatic Trigger Detection")
    print("=" * 60)

    detector = TriggerDetector()

    texts = [
        "We deployed SYNAPSE_LAYER v1.0.7 to PyPI and MCP Registry",
        "Decided to focus GOARQIA on enterprise architecture consulting",
        "Critical bug found in NEXUMI authentication flow",
        "The weather is nice today",  # No triggers
    ]

    for text in texts:
        events = detector.detect(text)
        if events:
            for e in events:
                print(f"  \u2713 [{e.type}] {e.project} (importance={e.importance})")
        else:
            print(f"  \u2717 No triggers: \"{text[:50]}...\"")


def demo_policy_evaluation():
    """Pattern 3: Policy engine decides what to save."""
    print("\n" + "=" * 60)
    print("Pattern 3: Policy Evaluation")
    print("=" * 60)

    policy = PolicyEngine(mode="oss")

    # Good event — should be approved
    event_ok = AutoSaveEvent(
        content="Launched SAFEZAP_BRASIL beta to first 100 users",
        project="SAFEZAP_BRASIL",
        type="[MILESTONE]",
        importance=4,
    )
    decision = policy.evaluate(event_ok)
    print(f"  Milestone: should_save={decision.should_save}, "
          f"importance={decision.adjusted_importance}")

    # Blocked event — contains a secret
    event_blocked = AutoSaveEvent(
        content="Deploy with api_key=sk-abcdef1234567890abcdef1234567890",
        project="OFFLY",
        type="[AUTO-OP]",
        importance=3,
    )
    decision = policy.evaluate(event_blocked)
    print(f"  Secret: should_save={decision.should_save}, "
          f"reason={decision.reason}")

    # Low importance in OSS mode
    event_low = AutoSaveEvent(
        content="Minor config change",
        project="GOARQIA",
        type="[AUTO-OP]",
        importance=1,
    )
    decision = policy.evaluate(event_low)
    print(f"  Low imp (OSS): should_save={decision.should_save}, "
          f"reason={decision.reason}")


if __name__ == "__main__":
    print("Synapse Layer — Auto-Save Engine Demo")
    print("Your AI agents remember what matters, forget what's sensitive.")

    demo_event_creation()
    demo_trigger_detection()
    demo_policy_evaluation()

    print("\n\u2705 Demo complete.")
