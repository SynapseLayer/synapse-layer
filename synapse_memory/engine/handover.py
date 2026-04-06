"""
NeuralHandover™ — Persistence-First Handover with Status Ledger

Secure, fault-tolerant context transfer between AI agents with:

    - **Status Ledger**: Every handover is vault-persisted with state
      tracking (PENDING → ACCEPTED → COMPLETED | FAILED | EXPIRED).
    - **JWT Tokenization**: Handover packages are signed HMAC-SHA256
      tokens carrying origin_agent, target_agent, user_id, and scope.
    - **Automatic Fallback**: If the target agent fails to accept,
      an Emergency Checkpoint is created with the full context.
    - **Grace Period & TTL**: Expired handovers auto-generate a
      compact summary instead of returning raw context data.
    - **Pipeline Integration**: Content is sanitized and intent-validated
      before being packaged into the handover token.

Architecture:
    Agent A (origin) → sanitize → validate → sign JWT → vault PENDING
    Agent B (target) → verify JWT → accept → vault COMPLETED
    Failure           → Emergency Checkpoint → vault FAILED
    TTL Expired       → Summary Generation → vault EXPIRED

Author: Security & Architecture Team @ Synapse Layer
License: Apache 2.0
"""

import hashlib
import hmac
import json
import base64
import time
import logging
import secrets
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..sanitizer import SynapseSanitizer, SanitizationResult
from .validator import SynapseValidator, ValidationResult, IntentCategory

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Handover State Machine
# ══════════════════════════════════════════════════════════════════════

class HandoverStatus(Enum):
    """Lifecycle states for a Neural Handover™ package.

    State transitions::

        PENDING → ACCEPTED → COMPLETED
        PENDING → FAILED (fallback triggered)
        PENDING → EXPIRED (TTL exceeded, summary generated)
    """

    PENDING   = "pending"     # Created, awaiting target agent
    ACCEPTED  = "accepted"    # Target agent acknowledged receipt
    COMPLETED = "completed"   # Full context transferred successfully
    FAILED    = "failed"      # Target agent failed; emergency checkpoint created
    EXPIRED   = "expired"     # TTL exceeded; summary generated in place of raw data


# ══════════════════════════════════════════════════════════════════════
#  Data Contracts
# ══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class HandoverToken:
    """Signed JWT-style token for cross-agent context transfer.

    The token is HMAC-SHA256 signed and carries the full handover
    metadata.  Verification is mandatory before acceptance.
    """

    token_id: str              # Unique handover identifier
    origin_agent: str          # Source agent ID
    target_agent: str          # Destination agent ID
    user_id: str               # Owning user
    scope: str                 # Access scope (e.g., "full", "read_only", "summary")
    issued_at: float           # Unix timestamp
    expires_at: float          # Unix timestamp (issued_at + ttl)
    signature: str             # HMAC-SHA256 of header.payload
    encoded_token: str         # Base64 encoded header.payload.signature


@dataclass
class HandoverPackage:
    """Full handover record persisted in the Status Ledger."""

    # ── Identity ─────────────────────────────────────────────
    handover_id: str
    token: HandoverToken
    status: HandoverStatus

    # ── Payload ──────────────────────────────────────────────
    context_data: List[Dict[str, Any]]   # Sanitized memories to transfer
    memory_count: int                     # Number of memories in payload
    intent_summary: Dict[str, int]        # {category: count}

    # ── Validation ───────────────────────────────────────────
    sanitized: bool
    validation_applied: bool
    content_hash: str                     # SHA-256 of full payload

    # ── Lifecycle ───────────────────────────────────────────
    created_at: float
    accepted_at: Optional[float] = None
    completed_at: Optional[float] = None
    failed_at: Optional[float] = None
    expired_at: Optional[float] = None

    # ── Fallback ─────────────────────────────────────────────
    emergency_checkpoint: Optional[Dict[str, Any]] = None
    grace_summary: Optional[str] = None
    error_reason: Optional[str] = None


@dataclass(frozen=True)
class HandoverResult:
    """Public-facing result returned by handover operations."""

    handover_id: str
    status: HandoverStatus
    token_encoded: str          # The signed JWT to transmit to target agent
    origin_agent: str
    target_agent: str
    user_id: str
    memory_count: int
    content_hash: str
    created_at: float
    sanitized: bool
    validation_applied: bool


# ══════════════════════════════════════════════════════════════════════
#  Handover Engine
# ══════════════════════════════════════════════════════════════════════

class NeuralHandover:
    """Persistence-First Neural Handover™ Engine.

    Manages secure, fault-tolerant context transfer between AI agents
    with a full Status Ledger for audit and recovery.

    Features:
        - HMAC-SHA256 signed JWT tokens for tamper-proof handover
        - Status Ledger: PENDING → ACCEPTED → COMPLETED | FAILED | EXPIRED
        - Automatic fallback with Emergency Checkpoint on failure
        - Grace Period: expired handovers return summaries, not raw data
        - Full integration with SynapseSanitizer and SynapseValidator

    Usage::

        handover = NeuralHandover(signing_key="your-256-bit-secret")

        # Agent A creates handover
        result = handover.create_handover(
            origin_agent="gpt-4",
            target_agent="claude-3.5",
            user_id="user-123",
            memories=[{"content": "User prefers dark mode", "confidence": 0.95}],
        )

        # Agent B accepts
        package = handover.accept_handover(result.handover_id)

        # Or retrieve latest for a user
        latest = handover.get_latest_handover(user_id="user-123")
    """

    # ── Defaults ───────────────────────────────────────────────
    DEFAULT_TTL: int = 3600             # 1 hour
    GRACE_PERIOD: int = 900             # 15 minutes after TTL
    MAX_MEMORIES_PER_HANDOVER: int = 500

    def __init__(
        self,
        signing_key: Optional[str] = None,
        *,
        ttl: int = 3600,
        sanitize: bool = True,
        validate: bool = True,
    ) -> None:
        """Initialize the handover engine.

        Args:
            signing_key: HMAC-SHA256 key for token signing.
                         Auto-generated (32 bytes) if not provided.
            ttl: Time-to-live in seconds for handover packages.
            sanitize: Run content through SynapseSanitizer before packaging.
            validate: Run content through SynapseValidator before packaging.
        """
        self._signing_key = (
            signing_key.encode() if signing_key
            else secrets.token_bytes(32)
        )
        self._ttl = max(ttl, 60)  # Minimum 60 seconds
        self._sanitize = sanitize
        self._validate = validate

        self._sanitizer = SynapseSanitizer() if sanitize else None
        self._validator = SynapseValidator(enable_self_healing=True) if validate else None

        # ── Status Ledger (in-memory; production uses PostgreSQL) ──
        self._ledger: Dict[str, HandoverPackage] = {}
        # Index: user_id → [handover_id, ...] ordered by created_at
        self._user_index: Dict[str, List[str]] = {}

        logger.info(
            "NeuralHandover initialized (ttl=%ds, sanitize=%s, validate=%s)",
            self._ttl, sanitize, validate,
        )

    # ══════════════════════════════════════════════════════════════
    #  create_handover()
    # ══════════════════════════════════════════════════════════════

    def create_handover(
        self,
        origin_agent: str,
        target_agent: str,
        user_id: str,
        memories: List[Dict[str, Any]],
        *,
        scope: str = "full",
    ) -> HandoverResult:
        """Create a new handover package and persist it as PENDING.

        Pipeline:
            1. Validate inputs
            2. Sanitize each memory content
            3. Validate intent for each memory
            4. Sign JWT token
            5. Persist to Status Ledger as PENDING
            6. Return HandoverResult with signed token

        Args:
            origin_agent: ID of the source agent.
            target_agent: ID of the destination agent.
            user_id: Owning user ID.
            memories: List of dicts, each with at least 'content' key.
            scope: Access scope for the target agent.

        Returns:
            HandoverResult with handover_id and signed token.

        Raises:
            ValueError: On invalid inputs or exceeding limits.
        """
        # ── Input validation ─────────────────────────────────────
        if not origin_agent or not target_agent or not user_id:
            raise ValueError(
                "origin_agent, target_agent, and user_id are required."
            )
        if origin_agent == target_agent:
            raise ValueError("origin_agent and target_agent must differ.")
        if not memories:
            raise ValueError("At least one memory is required.")
        if len(memories) > self.MAX_MEMORIES_PER_HANDOVER:
            raise ValueError(
                f"Exceeded max memories per handover "
                f"({len(memories)} > {self.MAX_MEMORIES_PER_HANDOVER})."
            )

        now = time.time()

        # ── Process memories through pipeline ────────────────────
        processed_memories: List[Dict[str, Any]] = []
        intent_summary: Dict[str, int] = {}
        all_sanitized = True
        all_validated = True

        for mem in memories:
            content = mem.get('content', '')
            confidence = mem.get('confidence', 0.9)

            if not content:
                continue

            processed: Dict[str, Any] = {
                'content': content,
                'confidence': confidence,
            }

            # Sanitize
            if self._sanitizer:
                san_result = self._sanitizer.sanitize_content(content)
                processed['content'] = san_result.sanitized_content
                processed['pii_removed'] = san_result.pii_count
                processed['risk_score'] = san_result.risk_score
            else:
                all_sanitized = False

            # Validate intent
            if self._validator:
                val_result = self._validator.validate_intent(
                    processed['content'],
                    agent_confidence=confidence,
                )
                processed['intent'] = val_result.final_intent.value
                processed['source_type'] = val_result.source_type
                processed['is_critical'] = val_result.is_critical

                cat = val_result.final_intent.value
                intent_summary[cat] = intent_summary.get(cat, 0) + 1
            else:
                all_validated = False

            processed_memories.append(processed)

        if not processed_memories:
            raise ValueError("No valid memories after processing.")

        # ── Generate handover ID & content hash ───────────────────
        payload_json = json.dumps(
            processed_memories, sort_keys=True, ensure_ascii=False
        )
        content_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        handover_id = f"ho_{content_hash[:24]}"

        # ── Sign JWT token ───────────────────────────────────────
        token = self._sign_token(
            token_id=handover_id,
            origin_agent=origin_agent,
            target_agent=target_agent,
            user_id=user_id,
            scope=scope,
            issued_at=now,
            expires_at=now + self._ttl,
        )

        # ── Persist to ledger as PENDING ─────────────────────────
        package = HandoverPackage(
            handover_id=handover_id,
            token=token,
            status=HandoverStatus.PENDING,
            context_data=processed_memories,
            memory_count=len(processed_memories),
            intent_summary=intent_summary,
            sanitized=all_sanitized,
            validation_applied=all_validated,
            content_hash=content_hash,
            created_at=now,
        )

        self._ledger[handover_id] = package

        # Update user index
        if user_id not in self._user_index:
            self._user_index[user_id] = []
        self._user_index[user_id].append(handover_id)

        logger.info(
            "Handover created: id=%s, origin=%s, target=%s, "
            "user=%s, memories=%d, status=PENDING",
            handover_id, origin_agent, target_agent,
            user_id, len(processed_memories),
        )

        return HandoverResult(
            handover_id=handover_id,
            status=HandoverStatus.PENDING,
            token_encoded=token.encoded_token,
            origin_agent=origin_agent,
            target_agent=target_agent,
            user_id=user_id,
            memory_count=len(processed_memories),
            content_hash=content_hash,
            created_at=now,
            sanitized=all_sanitized,
            validation_applied=all_validated,
        )

    # ══════════════════════════════════════════════════════════════
    #  accept_handover()
    # ══════════════════════════════════════════════════════════════

    def accept_handover(
        self,
        handover_id: str,
        accepting_agent: Optional[str] = None,
    ) -> HandoverPackage:
        """Accept a pending handover and transition to ACCEPTED/COMPLETED.

        Verifies the JWT signature, checks TTL, and returns the full
        context data.  If the TTL has expired but is within the grace
        period, a summary is generated instead of raw data.

        Args:
            handover_id: The handover to accept.
            accepting_agent: Optional agent ID for verification.

        Returns:
            The full HandoverPackage (status updated).

        Raises:
            KeyError: If handover_id not found.
            PermissionError: If accepting_agent doesn't match target.
            TimeoutError: If TTL + grace period exceeded.
        """
        package = self._get_package(handover_id)
        now = time.time()

        # Verify agent identity (if provided)
        if accepting_agent and accepting_agent != package.token.target_agent:
            raise PermissionError(
                f"Agent '{accepting_agent}' is not the target agent "
                f"for handover {handover_id}. "
                f"Expected: '{package.token.target_agent}'."
            )

        # Verify signature
        if not self._verify_token(package.token):
            self._fail_handover(package, "JWT signature verification failed")
            raise PermissionError("Handover token signature is invalid.")

        # Check TTL
        expires_at = package.token.expires_at
        grace_deadline = expires_at + self.GRACE_PERIOD

        if now > grace_deadline:
            # Beyond grace period — fully expired
            package.status = HandoverStatus.EXPIRED
            package.expired_at = now
            package.grace_summary = self._generate_summary(package)
            logger.warning(
                "Handover %s expired beyond grace period (%.0fs over)",
                handover_id, now - grace_deadline,
            )
            raise TimeoutError(
                f"Handover {handover_id} expired. "
                f"Grace period ended {now - grace_deadline:.0f}s ago."
            )

        if now > expires_at:
            # Within grace period — return summary, not raw data
            package.status = HandoverStatus.EXPIRED
            package.expired_at = now
            package.grace_summary = self._generate_summary(package)
            package.context_data = []  # Clear raw data
            logger.info(
                "Handover %s in grace period — returning summary",
                handover_id,
            )
            return package

        # Valid — transition PENDING → ACCEPTED → COMPLETED
        package.status = HandoverStatus.ACCEPTED
        package.accepted_at = now

        # Immediately complete (in production, target agent confirms)
        package.status = HandoverStatus.COMPLETED
        package.completed_at = now

        logger.info(
            "Handover %s accepted and completed: %s → %s (%d memories)",
            handover_id, package.token.origin_agent,
            package.token.target_agent, package.memory_count,
        )

        return package

    # ══════════════════════════════════════════════════════════════
    #  fail_handover()  —  Automatic Fallback
    # ══════════════════════════════════════════════════════════════

    def fail_handover(
        self,
        handover_id: str,
        reason: str = "Target agent unreachable",
    ) -> HandoverPackage:
        """Mark handover as FAILED and create Emergency Checkpoint.

        The full context data is preserved in the emergency checkpoint
        so recovery is always possible.

        Args:
            handover_id: The handover to fail.
            reason: Human-readable failure reason.

        Returns:
            Updated HandoverPackage with emergency_checkpoint.
        """
        package = self._get_package(handover_id)
        return self._fail_handover(package, reason)

    # ══════════════════════════════════════════════════════════════
    #  get_latest_handover()
    # ══════════════════════════════════════════════════════════════

    def get_latest_handover(
        self,
        user_id: str,
        *,
        status_filter: Optional[HandoverStatus] = None,
    ) -> Optional[HandoverPackage]:
        """Retrieve the most recent handover for a user.

        If the handover has expired but is within the grace period,
        a summary is auto-generated and the raw data is cleared.

        Args:
            user_id: The user to query.
            status_filter: If provided, only return handovers in this status.

        Returns:
            The latest HandoverPackage, or None if no handovers exist.
        """
        handover_ids = self._user_index.get(user_id, [])
        if not handover_ids:
            return None

        now = time.time()

        # Walk backward (newest first)
        for hid in reversed(handover_ids):
            package = self._ledger.get(hid)
            if package is None:
                continue

            # Auto-expire if TTL exceeded
            if (
                package.status == HandoverStatus.PENDING
                and now > package.token.expires_at
            ):
                if now <= package.token.expires_at + self.GRACE_PERIOD:
                    package.status = HandoverStatus.EXPIRED
                    package.expired_at = now
                    package.grace_summary = self._generate_summary(package)
                    package.context_data = []
                    logger.info(
                        "Auto-expired handover %s during lookup (grace period)",
                        hid,
                    )
                else:
                    package.status = HandoverStatus.EXPIRED
                    package.expired_at = now
                    package.grace_summary = self._generate_summary(package)
                    package.context_data = []

            if status_filter and package.status != status_filter:
                continue

            return package

        return None

    # ══════════════════════════════════════════════════════════════
    #  verify_token()  —  Public verification for target agents
    # ══════════════════════════════════════════════════════════════

    def verify_token_string(self, encoded_token: str) -> Dict[str, Any]:
        """Verify and decode a handover token string.

        Args:
            encoded_token: The base64-encoded token string.

        Returns:
            Decoded payload dict if signature is valid.

        Raises:
            PermissionError: If signature verification fails.
            ValueError: If token format is invalid.
        """
        try:
            parts = encoded_token.split('.')
            if len(parts) != 3:
                raise ValueError("Invalid token format (expected 3 parts).")

            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}".encode()
            expected_sig = hmac.new(
                self._signing_key, message, hashlib.sha256
            ).digest()
            provided_sig = base64.urlsafe_b64decode(sig_b64 + '==')

            if not hmac.compare_digest(expected_sig, provided_sig):
                raise PermissionError("Token signature verification failed.")

            # Decode payload
            payload_json = base64.urlsafe_b64decode(
                payload_b64 + '=='
            ).decode()
            return json.loads(payload_json)

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Token decode error: {e}") from e

    # ══════════════════════════════════════════════════════════════
    #  get_ledger_stats()
    # ══════════════════════════════════════════════════════════════

    def get_ledger_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics for the Status Ledger."""
        status_counts: Dict[str, int] = {}
        for pkg in self._ledger.values():
            s = pkg.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            'total_handovers': len(self._ledger),
            'total_users': len(self._user_index),
            'status_counts': status_counts,
        }

    # ══════════════════════════════════════════════════════════════
    #  Private Helpers
    # ══════════════════════════════════════════════════════════════

    def _sign_token(
        self,
        token_id: str,
        origin_agent: str,
        target_agent: str,
        user_id: str,
        scope: str,
        issued_at: float,
        expires_at: float,
    ) -> HandoverToken:
        """Create and sign a JWT-style handover token."""
        header = {
            'alg': 'HS256',
            'typ': 'SHT',  # Synapse Handover Token
        }
        payload = {
            'tid': token_id,
            'org': origin_agent,
            'tgt': target_agent,
            'uid': user_id,
            'scp': scope,
            'iat': issued_at,
            'exp': expires_at,
        }

        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b'=').decode()

        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b'=').decode()

        message = f"{header_b64}.{payload_b64}".encode()
        signature = hmac.new(
            self._signing_key, message, hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

        encoded = f"{header_b64}.{payload_b64}.{sig_b64}"

        return HandoverToken(
            token_id=token_id,
            origin_agent=origin_agent,
            target_agent=target_agent,
            user_id=user_id,
            scope=scope,
            issued_at=issued_at,
            expires_at=expires_at,
            signature=sig_b64,
            encoded_token=encoded,
        )

    def _verify_token(self, token: HandoverToken) -> bool:
        """Verify HMAC-SHA256 signature of a handover token."""
        try:
            parts = token.encoded_token.split('.')
            if len(parts) != 3:
                return False

            header_b64, payload_b64, sig_b64 = parts
            message = f"{header_b64}.{payload_b64}".encode()

            expected_sig = hmac.new(
                self._signing_key, message, hashlib.sha256
            ).digest()
            provided_sig = base64.urlsafe_b64decode(sig_b64 + '==')

            return hmac.compare_digest(expected_sig, provided_sig)

        except Exception:
            return False

    def _get_package(self, handover_id: str) -> HandoverPackage:
        """Retrieve a package or raise KeyError."""
        package = self._ledger.get(handover_id)
        if package is None:
            raise KeyError(f"Handover '{handover_id}' not found in ledger.")
        return package

    def _fail_handover(
        self,
        package: HandoverPackage,
        reason: str,
    ) -> HandoverPackage:
        """Transition to FAILED and create emergency checkpoint."""
        now = time.time()
        package.status = HandoverStatus.FAILED
        package.failed_at = now
        package.error_reason = reason

        # Emergency Checkpoint: preserve full context for recovery
        package.emergency_checkpoint = {
            'handover_id': package.handover_id,
            'origin_agent': package.token.origin_agent,
            'target_agent': package.token.target_agent,
            'user_id': package.token.user_id,
            'memory_count': package.memory_count,
            'intent_summary': package.intent_summary,
            'content_hash': package.content_hash,
            'context_snapshot': package.context_data[:],  # Full copy
            'failure_reason': reason,
            'checkpoint_at': now,
        }

        logger.error(
            "Handover %s FAILED: %s — Emergency checkpoint created",
            package.handover_id, reason,
        )

        return package

    @staticmethod
    def _generate_summary(package: HandoverPackage) -> str:
        """Generate a compact summary from expired handover context.

        Used during grace period to return useful information
        without exposing raw memory data.
        """
        parts: List[str] = [
            f"Handover Summary (expired): {package.handover_id}",
            f"From: {package.token.origin_agent} → {package.token.target_agent}",
            f"User: {package.token.user_id}",
            f"Memories: {package.memory_count}",
        ]

        if package.intent_summary:
            intent_str = ", ".join(
                f"{k}: {v}" for k, v in package.intent_summary.items()
            )
            parts.append(f"Intent distribution: {intent_str}")

        # Extract key content snippets (first 80 chars each)
        for i, mem in enumerate(package.context_data[:5]):
            content = mem.get('content', '')[:80]
            if content:
                parts.append(f"  [{i+1}] {content}...")

        return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════
#  Inline Tests (run with: python -m synapse_memory.engine.handover)
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("NeuralHandover™ — Inline Test Suite (v1.0.6)")
    print("=" * 60)

    KEY = "test-signing-key-256-bit-minimum!"
    ho = NeuralHandover(signing_key=KEY, ttl=5)  # 5s TTL for testing

    # Test 1: Create handover
    r1 = ho.create_handover(
        origin_agent="gpt-4",
        target_agent="claude-3.5",
        user_id="user-123",
        memories=[
            {"content": "User prefers dark mode and concise answers", "confidence": 0.95},
            {"content": "Important meeting scheduled for today", "confidence": 0.88},
        ],
    )
    assert r1.status == HandoverStatus.PENDING
    assert r1.memory_count == 2
    assert r1.sanitized is True
    assert r1.validation_applied is True
    assert r1.token_encoded
    print(f"[PASS] Create: id={r1.handover_id}, memories={r1.memory_count}, "
          f"status={r1.status.value}")

    # Test 2: Accept handover
    pkg2 = ho.accept_handover(r1.handover_id, accepting_agent="claude-3.5")
    assert pkg2.status == HandoverStatus.COMPLETED
    assert pkg2.completed_at is not None
    assert len(pkg2.context_data) == 2
    print(f"[PASS] Accept: status={pkg2.status.value}, "
          f"memories={len(pkg2.context_data)}")

    # Test 3: Wrong agent rejection
    r3 = ho.create_handover(
        origin_agent="gpt-4",
        target_agent="claude-3.5",
        user_id="user-456",
        memories=[{"content": "Test memory for wrong agent", "confidence": 0.9}],
    )
    try:
        ho.accept_handover(r3.handover_id, accepting_agent="gemini-1.5")
        assert False, "Should have raised PermissionError"
    except PermissionError:
        print("[PASS] Wrong agent rejected")

    # Test 4: Fail handover with emergency checkpoint
    r4 = ho.create_handover(
        origin_agent="gpt-4",
        target_agent="llama-3",
        user_id="user-789",
        memories=[{"content": "Critical security configuration data", "confidence": 0.99}],
    )
    failed_pkg = ho.fail_handover(r4.handover_id, reason="Target agent crashed")
    assert failed_pkg.status == HandoverStatus.FAILED
    assert failed_pkg.emergency_checkpoint is not None
    assert failed_pkg.emergency_checkpoint['failure_reason'] == "Target agent crashed"
    assert len(failed_pkg.emergency_checkpoint['context_snapshot']) == 1
    print(f"[PASS] Fallback: status={failed_pkg.status.value}, "
          f"checkpoint has {len(failed_pkg.emergency_checkpoint['context_snapshot'])} memories")

    # Test 5: get_latest_handover
    latest = ho.get_latest_handover(user_id="user-123")
    assert latest is not None
    assert latest.handover_id == r1.handover_id
    print(f"[PASS] get_latest: id={latest.handover_id}, status={latest.status.value}")

    # Test 6: get_latest for nonexistent user
    none_result = ho.get_latest_handover(user_id="nonexistent")
    assert none_result is None
    print("[PASS] get_latest: None for nonexistent user")

    # Test 7: Token verification
    decoded = ho.verify_token_string(r1.token_encoded)
    assert decoded['org'] == 'gpt-4'
    assert decoded['tgt'] == 'claude-3.5'
    assert decoded['uid'] == 'user-123'
    print(f"[PASS] Token verify: org={decoded['org']}, tgt={decoded['tgt']}")

    # Test 8: Grace period (TTL=5s, wait and test)
    import time as _time
    r8 = ho.create_handover(
        origin_agent="gpt-4",
        target_agent="claude-3.5",
        user_id="user-grace",
        memories=[{"content": "Memory that will expire", "confidence": 0.9}],
    )
    # Manually expire the token for testing
    ho._ledger[r8.handover_id].token = HandoverToken(
        token_id=r8.handover_id,
        origin_agent="gpt-4",
        target_agent="claude-3.5",
        user_id="user-grace",
        scope="full",
        issued_at=time.time() - 100,
        expires_at=time.time() - 10,  # Expired 10s ago
        signature=ho._ledger[r8.handover_id].token.signature,
        encoded_token=ho._ledger[r8.handover_id].token.encoded_token,
    )
    grace_pkg = ho.accept_handover(r8.handover_id)
    assert grace_pkg.status == HandoverStatus.EXPIRED
    assert grace_pkg.grace_summary is not None
    assert grace_pkg.context_data == []  # Raw data cleared
    print(f"[PASS] Grace period: summary generated, raw data cleared")

    # Test 9: Ledger stats
    stats = ho.get_ledger_stats()
    assert stats['total_handovers'] >= 4
    print(f"[PASS] Ledger stats: {stats}")

    # Test 10: Input validation
    try:
        ho.create_handover(
            origin_agent="gpt-4",
            target_agent="gpt-4",  # Same agent
            user_id="user-x",
            memories=[{"content": "test"}],
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Same agent rejected")

    try:
        ho.create_handover(
            origin_agent="gpt-4",
            target_agent="claude",
            user_id="user-x",
            memories=[],  # Empty
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        print("[PASS] Empty memories rejected")

    # Test 11: PII sanitization in handover
    r11 = ho.create_handover(
        origin_agent="gpt-4",
        target_agent="claude-3.5",
        user_id="user-pii",
        memories=[{"content": "Contact john@acme.com about the project", "confidence": 0.9}],
    )
    pkg11 = ho.accept_handover(r11.handover_id)
    assert 'john@acme.com' not in pkg11.context_data[0]['content']
    assert pkg11.context_data[0].get('pii_removed', 0) >= 1
    print(f"[PASS] PII sanitized in handover: "
          f"{pkg11.context_data[0].get('pii_removed')} items removed")

    print(f"\n✅ All inline tests passed.")
