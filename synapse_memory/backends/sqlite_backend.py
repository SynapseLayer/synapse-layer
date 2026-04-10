"""
Synapse Layer — SQLite Backend

Zero-config persistent storage using Python's built-in sqlite3.
No external dependencies required.

Usage::

    from synapse_memory import SynapseMemory
    from synapse_memory.backends import SqliteBackend

    memory = SynapseMemory(
        agent_id="my-agent",
        backend=SqliteBackend("./memories.db"),
    )
    await memory.store("User prefers dark mode")
    # Process can restart — data persists
    results = await memory.recall("preferences")

Author : Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_PATH = os.path.join(os.getcwd(), ".synapse", "memories.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id     TEXT PRIMARY KEY,
    agent_id      TEXT NOT NULL,
    content       TEXT NOT NULL,
    trust_quotient REAL DEFAULT 0.0,
    confidence    REAL DEFAULT 0.9,
    intent        TEXT DEFAULT 'unknown',
    is_critical   INTEGER DEFAULT 0,
    source_type   TEXT DEFAULT 'inference',
    metadata_json TEXT DEFAULT '{}',
    timestamp     REAL NOT NULL,
    content_lower TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_agent ON memories(agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories(timestamp);
CREATE INDEX IF NOT EXISTS idx_memories_tq ON memories(trust_quotient);
"""


class SqliteBackend:
    """Persistent SQLite storage for SynapseMemory.

    Thread-safe via connection-per-thread with WAL mode.
    No external dependencies — uses Python stdlib sqlite3.

    Args:
        path: Database file path. Default: .synapse/memories.db
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _DEFAULT_PATH
        self._local = threading.local()

        # Ensure directory exists
        db_dir = os.path.dirname(self._path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        # Initialize schema
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.commit()

        logger.info("SqliteBackend initialized: path=%s", self._path)

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def save(self, record: Dict[str, Any]) -> str:
        """Persist a memory record."""
        memory_id = record.get("memory_id", "")
        agent_id = record.get("agent_id", "")
        content = record.get("content", "")
        trust_quotient = record.get("trust_quotient", 0.0)
        confidence = record.get("confidence", 0.9)
        intent = record.get("intent", "unknown")
        is_critical = 1 if record.get("is_critical", False) else 0
        source_type = record.get("source_type", "inference")
        metadata = record.get("metadata", {})
        timestamp = record.get("timestamp", 0.0)

        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO memories
                (memory_id, agent_id, content, trust_quotient, confidence,
                 intent, is_critical, source_type, metadata_json, timestamp,
                 content_lower)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory_id, agent_id, content, trust_quotient, confidence,
                intent, is_critical, source_type,
                json.dumps(metadata, ensure_ascii=False),
                timestamp, content.lower(),
            ),
        )
        conn.commit()
        logger.debug("Saved memory %s for agent %s", memory_id, agent_id)
        return memory_id

    def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories matching query via keyword search.

        Uses SQLite LIKE for substring matching on content_lower.
        Results ordered by trust_quotient DESC, timestamp DESC.
        """
        conn = self._get_conn()
        words = [w.strip() for w in query.lower().split() if w.strip()]

        if not words:
            # No query — return most recent
            sql = "SELECT * FROM memories"
            params: list = []
            if agent_id:
                sql += " WHERE agent_id = ?"
                params.append(agent_id)
            sql += " ORDER BY trust_quotient DESC, timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

        # Build keyword matching: each word must appear
        conditions = []
        params = []
        for w in words[:10]:  # Cap at 10 words
            conditions.append("content_lower LIKE ?")
            params.append(f"%{w}%")

        where = " OR ".join(conditions)
        if agent_id:
            where = f"({where}) AND agent_id = ?"
            params.append(agent_id)

        sql = f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY trust_quotient DESC, timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete(self, memory_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM memories WHERE memory_id = ?", (memory_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def clear(self, agent_id: Optional[str] = None) -> int:
        conn = self._get_conn()
        if agent_id is None:
            cursor = conn.execute("DELETE FROM memories")
        else:
            cursor = conn.execute(
                "DELETE FROM memories WHERE agent_id = ?", (agent_id,)
            )
        conn.commit()
        return cursor.rowcount

    def count(self, agent_id: Optional[str] = None) -> int:
        conn = self._get_conn()
        if agent_id is None:
            row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return row[0] if row else 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dict compatible with SynapseMemory."""
        d = dict(row)
        d["is_critical"] = bool(d.get("is_critical", 0))
        try:
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        d.pop("content_lower", None)
        return d

    def close(self) -> None:
        """Close the thread-local connection."""
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None

    def __repr__(self) -> str:
        return f"SqliteBackend(path={self._path!r})"
