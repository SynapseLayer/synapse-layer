-- ============================================================================
-- Synapse Layer — Auto-Save MCP Bridge: Database Schema
-- Target: Supabase (PostgreSQL 15+ with pgvector)
-- Region: sa-east-1
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- 1. MEMORIES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS memories (
    id            uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    content       text          NOT NULL,
    metadata      jsonb         NOT NULL DEFAULT '{}'::jsonb,
    embedding     vector(1536)  NULL,        -- NULL until backfill processes it
    project       text          NOT NULL,
    source_hash   text          NULL,        -- SHA-256 dedupe key
    created_at    timestamptz   NOT NULL DEFAULT now(),
    updated_at    timestamptz   NOT NULL DEFAULT now()
);

COMMENT ON TABLE memories IS 'Synapse Layer auto-save memories with async embedding pipeline';
COMMENT ON COLUMN memories.content IS 'PII-redacted content (raw content is NEVER stored)';
COMMENT ON COLUMN memories.embedding IS 'NULL until backfill_embeddings processes the row';
COMMENT ON COLUMN memories.source_hash IS 'SHA-256(project + normalized_content + stable_metadata) for dedup';

-- ============================================================================
-- 2. EMBEDDING JOBS TABLE (async queue)
-- ============================================================================
CREATE TABLE IF NOT EXISTS embedding_jobs (
    id            uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id     uuid          NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    status        text          NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    attempts      int           NOT NULL DEFAULT 0,
    max_attempts  int           NOT NULL DEFAULT 3,
    error_message text          NULL,
    created_at    timestamptz   NOT NULL DEFAULT now(),
    processed_at  timestamptz   NULL
);

COMMENT ON TABLE embedding_jobs IS 'Async embedding generation queue';

-- ============================================================================
-- 3. INDEXES
-- ============================================================================

-- Fast project + time range queries
CREATE INDEX IF NOT EXISTS idx_memories_project_created
    ON memories (project, created_at DESC);

-- JSONB metadata queries (tags, type, importance)
CREATE INDEX IF NOT EXISTS idx_memories_metadata_gin
    ON memories USING gin (metadata jsonb_path_ops);

-- Deduplication index (unique per project)
CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_source_hash_unique
    ON memories (project, source_hash)
    WHERE source_hash IS NOT NULL;

-- Embedding similarity search (HNSW — better recall than IVFFlat)
-- Only index rows that HAVE an embedding
CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw
    ON memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- Embedding jobs: fast pending job lookup
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_pending
    ON embedding_jobs (status, created_at ASC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_embedding_jobs_memory
    ON embedding_jobs (memory_id);

-- ============================================================================
-- 4. UPDATED_AT TRIGGER
-- ============================================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_memories_updated_at ON memories;
CREATE TRIGGER set_memories_updated_at
    BEFORE UPDATE ON memories
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- 5. ROW LEVEL SECURITY (RLS)
-- ============================================================================
-- Enable RLS on both tables
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS (used by the MCP server)
-- These policies restrict anon/authenticated access

-- Policy: users can only read memories from their own project
CREATE POLICY memories_select_own_project ON memories
    FOR SELECT
    USING (
        project = current_setting('request.jwt.claims', true)::jsonb ->> 'project'
    );

-- Policy: users can only insert into their own project
CREATE POLICY memories_insert_own_project ON memories
    FOR INSERT
    WITH CHECK (
        project = current_setting('request.jwt.claims', true)::jsonb ->> 'project'
    );

-- Policy: service role can do everything (for the MCP server backend)
CREATE POLICY memories_service_role ON memories
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY embedding_jobs_service_role ON embedding_jobs
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- ============================================================================
-- 6. HELPER VIEW: pending embeddings count per project
-- ============================================================================
CREATE OR REPLACE VIEW v_embedding_queue_stats AS
SELECT
    m.project,
    COUNT(*) FILTER (WHERE ej.status = 'pending')    AS pending,
    COUNT(*) FILTER (WHERE ej.status = 'processing')  AS processing,
    COUNT(*) FILTER (WHERE ej.status = 'completed')   AS completed,
    COUNT(*) FILTER (WHERE ej.status = 'failed')      AS failed
FROM embedding_jobs ej
JOIN memories m ON m.id = ej.memory_id
GROUP BY m.project;
