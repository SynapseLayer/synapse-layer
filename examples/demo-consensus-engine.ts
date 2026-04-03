/**
 * Synapse Layer — Trust Quotient™ Consensus Engine
 *
 * Intelligent conflict resolution algorithm that scores memories
 * based on Recency, Consistency, Confidence, and Relevance.
 *
 * Author: Security & Architecture Team
 * License: Apache 2.0
 * Version: 1.0.3 (FASE 1)
 */

interface Memory {
  id: string;
  agent_id: string;
  content: string;
  intent_category: string;
  confidence: number;  // 0.0–1.0 from SynapseValidator
  is_critical: boolean;
  created_at: Date;
  updated_at: Date;
}

interface SearchResult {
  memory: Memory;
  recency_score: number;      // 0.0–1.0
  consistency_score: number;  // 0.0–1.0
  confidence_score: number;   // 0.0–1.0 (from SynapseValidator)
  relevance_score: number;    // 0.0–1.0 (semantic similarity)
  trust_quotient: number;     // Final TQ score
}

interface ConflictResolutionResult {
  winner: SearchResult;
  loser: SearchResult;
  winner_tq: number;
  loser_tq: number;
  reason: string;
}

/**
 * Trust Quotient™ Algorithm
 *
 * TQ = (Recency × 0.4) + (Consistency × 0.3) + (Confidence × 0.2) + (Relevance × 0.1)
 *
 * - Recency (40%): How fresh the memory is (most recent = 1.0)
 * - Consistency (30%): Agreement with other memories in the agent's context
 * - Confidence (20%): Validation confidence from SynapseValidator (0.85–1.0)
 * - Relevance (10%): Semantic similarity to the current query
 */
class TrustQuotientEngine {
  /**
   * Calculate recency score based on how old the memory is
   *
   * @param createdAt - When the memory was created
   * @param currentTime - Current time reference
   * @param maxAgeInDays - Memories older than this get 0.0 score
   * @returns Score 0.0–1.0 (1.0 = just created, 0.0 = very old)
   */
  private calculateRecencyScore(
    createdAt: Date,
    currentTime: Date = new Date(),
    maxAgeInDays: number = 365
  ): number {
    const ageInMs = currentTime.getTime() - createdAt.getTime();
    const ageInDays = ageInMs / (1000 * 60 * 60 * 24);

    if (ageInDays > maxAgeInDays) {
      return 0.0;
    }

    // Linear decay: most recent = 1.0, at maxAge = 0.0
    const recencyScore = Math.max(0, 1 - ageInDays / maxAgeInDays);
    return Math.round(recencyScore * 100) / 100;
  }

  /**
   * Calculate consistency score by comparing with other memories
   *
   * This is a simplified implementation. In production, would:
   * 1. Fetch all memories for the agent
   * 2. Calculate semantic similarity between contents
   * 3. Find agreement/disagreement with existing context
   *
   * @param memory - The memory to score
   * @param otherMemories - All other memories for context
   * @returns Score 0.0–1.0 (1.0 = perfect agreement, 0.0 = contradicts)
   */
  private calculateConsistencyScore(
    memory: Memory,
    otherMemories: Memory[] = []
  ): number {
    if (otherMemories.length === 0) {
      // No other memories to compare against
      return 0.5; // Neutral score
    }

    // Simplified: check category consistency
    const sameCategory = otherMemories.filter(
      (m) => m.intent_category === memory.intent_category
    ).length;

    const consistency = sameCategory / otherMemories.length;
    return Math.round(consistency * 100) / 100;
  }

  /**
   * Confidence score comes directly from SynapseValidator
   *
   * @param validatorConfidence - Output from SynapseValidator.validate_intent()
   * @returns Score 0.0–1.0 (from SynapseValidator)
   */
  private calculateConfidenceScore(validatorConfidence: number): number {
    // Clamp to [0, 1] range
    return Math.max(0, Math.min(1, validatorConfidence));
  }

  /**
   * Relevance score based on semantic similarity
   *
   * In production, this would be:
   * 1. Convert query to embedding vector
   * 2. Calculate cosine similarity between vectors
   * 3. Return similarity score
   *
   * @param memoryEmbedding - Vector embedding of the memory
   * @param queryEmbedding - Vector embedding of the search query
   * @returns Score 0.0–1.0 (1.0 = perfect match)
   */
  private calculateRelevanceScore(
    memoryEmbedding: number[],
    queryEmbedding: number[]
  ): number {
    // Simplified: random for demo purposes
    // In production: use pgvector cosine similarity
    return Math.random();
  }

  /**
   * Calculate Trust Quotient™ score
   *
   * TQ = (Recency × 0.4) + (Consistency × 0.3) + (Confidence × 0.2) + (Relevance × 0.1)
   *
   * @param recency - Recency score (0–1)
   * @param consistency - Consistency score (0–1)
   * @param confidence - Confidence score (0–1)
   * @param relevance - Relevance score (0–1)
   * @returns Final TQ score (0–1)
   */
  calculateTrustQuotient(
    recency: number,
    consistency: number,
    confidence: number,
    relevance: number
  ): number {
    const tq =
      recency * 0.4 + consistency * 0.3 + confidence * 0.2 + relevance * 0.1;

    return Math.round(tq * 100) / 100;
  }

  /**
   * Score a memory for recall/search
   *
   * @param memory - The memory to score
   * @param queryEmbedding - Query vector for relevance
   * @param allMemories - All memories for consistency calculation
   * @returns SearchResult with all scores
   */
  scoreMemory(
    memory: Memory,
    queryEmbedding: number[],
    allMemories: Memory[] = []
  ): SearchResult {
    const recencyScore = this.calculateRecencyScore(memory.created_at);
    const consistencyScore = this.calculateConsistencyScore(
      memory,
      allMemories.filter((m) => m.id !== memory.id)
    );
    const confidenceScore = this.calculateConfidenceScore(memory.confidence);
    const relevanceScore = this.calculateRelevanceScore(
      new Array(1536).fill(0), // Placeholder embedding
      queryEmbedding
    );

    const trustQuotient = this.calculateTrustQuotient(
      recencyScore,
      consistencyScore,
      confidenceScore,
      relevanceScore
    );

    return {
      memory,
      recency_score: recencyScore,
      consistency_score: consistencyScore,
      confidence_score: confidenceScore,
      relevance_score: relevanceScore,
      trust_quotient: trustQuotient,
    };
  }

  /**
   * Resolve conflicts between multiple memories
   *
   * When memories contradict, the one with the highest TQ wins.
   * Tie-breaker: most recent timestamp.
   *
   * @param memories - Conflicting memories
   * @param queryEmbedding - Query vector for relevance
   * @returns Winner and loser with reasoning
   */
  resolveConflict(
    memories: Memory[],
    queryEmbedding: number[]
  ): ConflictResolutionResult {
    if (memories.length < 2) {
      throw new Error("Need at least 2 memories to resolve conflict");
    }

    // Score all memories
    const scoredMemories = memories.map((m) =>
      this.scoreMemory(m, queryEmbedding, memories)
    );

    // Sort by TQ descending, then by timestamp descending
    scoredMemories.sort((a, b) => {
      if (a.trust_quotient !== b.trust_quotient) {
        return b.trust_quotient - a.trust_quotient;
      }
      return b.memory.updated_at.getTime() - a.memory.updated_at.getTime();
    });

    const winner = scoredMemories[0];
    const loser = scoredMemories[1];

    let reason = `Winner TQ: ${winner.trust_quotient} > Loser TQ: ${loser.trust_quotient}`;

    if (winner.trust_quotient === loser.trust_quotient) {
      reason += ` (tie-breaker: more recent ${winner.memory.updated_at})`;
    }

    return {
      winner,
      loser,
      winner_tq: winner.trust_quotient,
      loser_tq: loser.trust_quotient,
      reason,
    };
  }
}

/**
 * DEMO: Trust Quotient in Action
 */
function demoTrustQuotient() {
  const engine = new TrustQuotientEngine();

  // Create sample memories
  const memory1: Memory = {
    id: "mem_001",
    agent_id: "agent_001",
    content: "User prefers concise answers in Portuguese",
    intent_category: "user_profile",
    confidence: 0.92, // From SynapseValidator
    is_critical: false,
    created_at: new Date("2026-04-03T10:00:00Z"),
    updated_at: new Date("2026-04-03T10:00:00Z"),
  };

  const memory2: Memory = {
    id: "mem_002",
    agent_id: "agent_001",
    content: "User prefers detailed English responses",
    intent_category: "user_profile",
    confidence: 0.65, // Lower confidence = conflicting info
    is_critical: false,
    created_at: new Date("2026-04-02T15:00:00Z"),
    updated_at: new Date("2026-04-02T15:00:00Z"),
  };

  console.log("╔════════════════════════════════════════════════════════════════╗");
  console.log("║     Synapse Layer — Trust Quotient™ Consensus Engine Demo       ║");
  console.log("╚════════════════════════════════════════════════════════════════╝\n");

  // Score individual memories
  console.log("MEMORY 1 SCORING:");
  const scored1 = engine.scoreMemory(memory1, new Array(1536).fill(0));
  console.log(`  Content: "${memory1.content}"`);
  console.log(`  Intent Category: ${memory1.intent_category}`);
  console.log(`  Validator Confidence: ${memory1.confidence}`);
  console.log(`  \n  TQ Components:`);
  console.log(`    Recency (40%):    ${scored1.recency_score}`);
  console.log(`    Consistency (30%): ${scored1.consistency_score}`);
  console.log(`    Confidence (20%):  ${scored1.confidence_score}`);
  console.log(`    Relevance (10%):   ${scored1.relevance_score}`);
  console.log(`  \n  ✓ TRUST QUOTIENT: ${scored1.trust_quotient}\n`);

  console.log("MEMORY 2 SCORING:");
  const scored2 = engine.scoreMemory(memory2, new Array(1536).fill(0));
  console.log(`  Content: "${memory2.content}"`);
  console.log(`  Intent Category: ${memory2.intent_category}`);
  console.log(`  Validator Confidence: ${memory2.confidence}`);
  console.log(`  \n  TQ Components:`);
  console.log(`    Recency (40%):    ${scored2.recency_score}`);
  console.log(`    Consistency (30%): ${scored2.consistency_score}`);
  console.log(`    Confidence (20%):  ${scored2.confidence_score}`);
  console.log(`    Relevance (10%):   ${scored2.relevance_score}`);
  console.log(`  \n  ✓ TRUST QUOTIENT: ${scored2.trust_quotient}\n`);

  // Resolve conflict
  console.log("CONFLICT RESOLUTION:");
  const resolution = engine.resolveConflict(
    [memory1, memory2],
    new Array(1536).fill(0)
  );
  console.log(`  ${resolution.reason}`);
  console.log(`  \n  ✓ WINNER: ${resolution.winner.memory.id}`);
  console.log(`    Content: "${resolution.winner.memory.content}"`);
  console.log(`    TQ: ${resolution.winner_tq}`);
  console.log(`  \n  ✗ LOSER: ${resolution.loser.memory.id}`);
  console.log(`    Content: "${resolution.loser.memory.content}"`);
  console.log(`    TQ: ${resolution.loser_tq}`);
  console.log(
    `  \n  🎯 Agent will use memory 1 (higher TQ, more recent, higher confidence)\n`
  );

  console.log(
    "╚════════════════════════════════════════════════════════════════╝\n"
  );
}

// Run demo if executed directly
if (require.main === module) {
  demoTrustQuotient();
}

export { TrustQuotientEngine, Memory, SearchResult, ConflictResolutionResult };
