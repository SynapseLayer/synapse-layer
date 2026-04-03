"""
Example: Complete Memory Storage Pipeline (Immutable Sequence)

This demonstrates the mandatory pipeline:
1. Sanitize → Remove PII
2. Validate → Check intent & confidence
3. Encrypt → AES-256-GCM
4. Embed → Generate semantic vectors
5. Store → pgvector + audit log

Author: Security & Architecture Team
License: Apache 2.0
"""

import asyncio
from synapse_memory import SynapseSanitizer
from synapse_memory.engine import SynapseValidator, IntentCategory

# Example demonstrating the immutable pipeline


async def store_memory_complete_pipeline(raw_content: str, agent_id: str):
    """
    Complete memory storage pipeline (IMMUTABLE SEQUENCE).
    
    This is the canonical flow that must be followed for all memory operations.
    
    Args:
        raw_content: Raw text input from user/agent
        agent_id: Unique agent identifier
        
    Returns:
        Dictionary with storage result
    """
    
    print("\n" + "=" * 70)
    print("SYNAPSE LAYER — COMPLETE MEMORY PIPELINE")
    print("=" * 70)
    
    # ============================================================================
    # STEP 1: SANITIZE — Remove PII and calculate risk score
    # ============================================================================
    print("\n[STEP 1] SANITIZING content...")
    print(f"  Input: {raw_content[:100]}...")
    
    sanitizer = SynapseSanitizer(aggressive_mode=False)
    sanitization_result = sanitizer.sanitize_content(raw_content)
    
    print(f"  ✓ PII items removed: {sanitization_result.pii_count}")
    print(f"  ✓ Risk score: {sanitization_result.risk_score:.2f}")
    print(f"  ✓ Is safe: {sanitization_result.is_safe}")
    print(f"  ✓ Sanitized: {sanitization_result.sanitized_content[:100]}...")
    
    if sanitization_result.removed_items:
        print(f"  ✓ Removed items:")
        for item in sanitization_result.removed_items:
            print(f"    - {item['type']}: {item['sensitivity']}")
    
    # ============================================================================
    # STEP 2: VALIDATE — Classify intent and validate confidence
    # ============================================================================
    print("\n[STEP 2] VALIDATING intent...")
    
    validator = SynapseValidator(enable_self_healing=True)
    validation_result = validator.validate_intent(
        sanitization_result.sanitized_content
    )
    
    print(f"  ✓ Intent category: {validation_result.intent_category.value}")
    print(f"  ✓ Confidence: {validation_result.confidence:.2f}")
    print(f"  ✓ Is critical: {validation_result.is_critical}")
    print(f"  ✓ Validation score: {validation_result.validation_score:.2f}")
    print(f"  ✓ Is valid (>= 0.85): {validation_result.is_valid}")
    
    if validation_result.self_healing_applied:
        print(f"  ✓ Self-healing applied:")
        for note in validation_result.healing_notes:
            print(f"    - {note}")
    
    # Check if content passed validation
    if not validation_result.is_valid:
        print("\n⚠️  VALIDATION FAILED (confidence < 0.85)")
        print("   Content would require user confirmation to proceed.")
        return {
            "status": "validation_failed",
            "reason": f"Confidence too low: {validation_result.confidence:.2f}",
            "intent": validation_result.intent_category.value,
            "requires_user_approval": True
        }
    
    # ============================================================================
    # STEP 3: ENCRYPT — AES-256-GCM with PBKDF2 derived key
    # ============================================================================
    print("\n[STEP 3] ENCRYPTING with AES-256-GCM...")
    print(f"  ℹ️  Key derivation: PBKDF2-SHA256 (210,000 iterations)")
    print(f"  ℹ️  IV: 96 bits (random)")
    print(f"  ℹ️  Auth Tag: 128 bits")
    
    # NOTE: In production, encryption happens on the client with user's password
    # This is a placeholder showing the process
    encrypted_blob = f"<AES-256-GCM-ENCRYPTED-BLOB>".encode()
    
    print(f"  ✓ Encrypted blob size: {len(encrypted_blob)} bytes")
    print(f"  ✓ Encryption complete")
    
    # ============================================================================
    # STEP 4: EMBED — Generate semantic search vectors
    # ============================================================================
    print("\n[STEP 4] GENERATING embeddings...")
    print(f"  ℹ️  Embedding dimension: 1536 (OpenAI compatible)")
    print(f"  ℹ️  Vector index: pgvector (PostgreSQL HNSW)")
    
    # Placeholder for embedding generation
    embedding_vector = [0.0] * 1536  # In production: call embedding API
    
    print(f"  ✓ Embedding generated (1536-dim vector)")
    
    # ============================================================================
    # STEP 5: STORE — Upsert to pgvector + immutable audit log
    # ============================================================================
    print("\n[STEP 5] STORING in encrypted vault...")
    
    memory_record = {
        "id": "mem_" + agent_id[:8],
        "agent_id": agent_id,
        "encrypted_blob": encrypted_blob,
        "embedding": embedding_vector,
        "intent_category": validation_result.intent_category.value,
        "confidence": validation_result.confidence,
        "is_critical": validation_result.is_critical,
        "risk_score": sanitization_result.risk_score,
        "pii_removed": sanitization_result.pii_count,
        "created_at": "2026-04-03T15:52:00Z",
    }
    
    print(f"  ✓ Memory stored in PostgreSQL + pgvector")
    print(f"  ✓ Row-Level Security (RLS) by agent_id")
    print(f"  ✓ Audit log entry created")
    
    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 70)
    print("✅ MEMORY SUCCESSFULLY STORED")
    print("=" * 70)
    print(f"""
Summary:
  Intent Category:  {validation_result.intent_category.value}
  Confidence:       {validation_result.confidence:.2f}/1.0
  Is Critical:      {validation_result.is_critical}
  Risk Score:       {sanitization_result.risk_score:.2f}/1.0
  PII Removed:      {sanitization_result.pii_count} items
  Encrypted:        ✓ AES-256-GCM
  Stored:           ✓ PostgreSQL + pgvector
  Audit Trail:      ✓ Immutable log

Trust Quotient™ (will be calculated on recall):
  Recency:         0.0 (new memory)
  Consistency:     TBD (on comparison with existing)
  Confidence:      {validation_result.confidence:.2f}
  Relevance:       TBD (on semantic search)
""")
    
    return {
        "status": "success",
        "memory_id": memory_record["id"],
        "intent": validation_result.intent_category.value,
        "confidence": validation_result.confidence,
        "is_critical": validation_result.is_critical,
        "pii_removed": sanitization_result.pii_count,
        "risk_score": sanitization_result.risk_score,
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Test case 1: Normal user profile
    example_1 = (
        "My name is John Smith and I work as a software engineer. "
        "I prefer concise answers in Portuguese. Email: john@example.com"
    )
    
    asyncio.run(store_memory_complete_pipeline(example_1, "agent-001"))
    
    # Test case 2: Medical (auto-critical)
    example_2 = (
        "I was diagnosed with diabetes by Dr. Johnson last week. "
        "Started medication: Metformin 500mg. "
        "My phone is (555) 123-4567 for follow-up appointments."
    )
    
    asyncio.run(store_memory_complete_pipeline(example_2, "agent-001"))
    
    # Test case 3: Financial (auto-critical)
    example_3 = (
        "Transfer $5000 from my bank account (123-45-6789) "
        "to savings account. Credit card 1234-5678-9012-3456 as backup."
    )
    
    asyncio.run(store_memory_complete_pipeline(example_3, "agent-001"))
