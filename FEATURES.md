# Synapse Layer — Features & Claims

> Contract between our public documentation and reality. Every claim in our
> READMEs, SDKs and skills traces to a line here. Reviewed on every release.
>
> This is the **public** matrix. Operational evidence (migrations, flags,
> test counts, deploy state) lives in the private evidence register.

**Last verified:** 2026-11-04
**Public versions:** MCP server `2.4.6` · PyPI `synapse-layer` `2.4.6`
**Status legend:** Shipped · Gated (deployed, flag off) · In progress · Experimental · Roadmap · Not claimed

## 1. Core memory

| Capability | Status | Known limits |
|---|---|---|
| Persistent memory across sessions and agents (MCP · REST · Python SDK) | Shipped | — |
| Full-text ∥ vector search; filters applied before ranking | Shipped | — |
| Exact dedup — scoped: personal memories dedup within the user; project memories dedup within the project | Shipped | Cross-scope duplicates return a consultative warning — never auto-merge |
| Configurable duplicate threshold per project | Shipped | Threshold is read from the stored project policy |
| Idempotent writes (`Idempotency-Key`) | Shipped | — |
| Recall requires a stated reason (governance) | Shipped | Enforced on plaintext exports |

## 2. Isolation & access

| Capability | Status | Known limits |
|---|---|---|
| Tenant isolation; fail-closed borders | Shipped | — |
| Personal plan: 1 user = 1 private mind | Shipped | Applies to personal workspaces only |
| Corporate: organizations → projects → memberships | Shipped | Roles at user, organization and project level |
| Visibility: own or shared-to-project | Shipped | — |
| Per-token recall ceiling (OWN / PROJECT / TENANT) with write denial | In progress | Legacy tokens run in compatibility mode during the telemetry window; the target behavior is not current |
| Agent registry + RBAC per agent/category | Roadmap | — |
| SSO / Entra ID / BYOC | Roadmap | — |

## 3. Lifecycle & retention

| Capability | Status | Known limits |
|---|---|---|
| Lifecycle states (active · needs_review · merged · superseded · quarantined · archived) | Shipped | — |
| Grace window before expiry | Shipped | Memory stays recallable during the window |
| Expiry surfaced in the curation queue | Shipped | Passive — no proactive notifications yet |
| No AI-initiated merge or deletion. Policy-based TTL/GC may delete expired data under configured retention rules, with an audit trail. Hard delete requires a documented reason. | Shipped (mechanism) | — |
| Full right-to-erase propagation (indexes, embeddings, caches, backups) + retention/legal-hold exceptions | In progress | **Not claimed as complete compliance** |
| Proactive pre-expiry notifications | Roadmap | — |

## 4. Curation (human-in-the-loop)

| Capability | Status | Known limits |
|---|---|---|
| Detect → suggest → human decides → audited apply/revert | Shipped | Originals preserved; reversible |
| Suggestions carry metadata only — never memory content | Shipped | — |
| Orphan detection + automated sweep of non-actionable suggestions | Shipped (with limitation) | Sweep dismissal is not yet reversible — in progress |
| Policy-based thresholds; organization/project inheritance; runtime policy resolution | Shipped (stored thresholds) · Gated (inheritance + resolver) | Gated paths are deployed behind a feature flag, default OFF pending canary |
| No AI-initiated merge or deletion of content | Shipped (with limitation) | The sweep may dismiss non-actionable *suggestions*; reversibility is evolving |

## 5. Security & privacy

| Capability | Status | Known limits |
|---|---|---|
| Encryption at rest, AES-256-GCM, server-side | Shipped | The service processes plaintext in memory — **not zero-knowledge** |
| Integrity verification (HMAC) + metadata redaction per scope | Shipped | — |
| PII sanitization on write | Shipped | — |
| Database RLS hardening (hosted deployment) | Shipped | — |
| Differential privacy on embeddings | Not claimed | Experimental noise only; API reports `differential_privacy: false` |

## 6. Audit & operations

| Capability | Status | Known limits |
|---|---|---|
| Append-only audit events (actor, role, justification — no content) | Shipped | — |
| Structural-only operational logs (no plaintext content, queries, tokens or emails) | Shipped | — |
| Health and status endpoints | Shipped | Authorization failures block data access, not status visibility |
| Quotas per agent | Shipped | — |
| Encrypted backups; restore validated on application data | Shipped (mechanism) | Formal RTO documentation pending |
| Measured token savings per agent | Roadmap | Metering exists; published study does not |

## 7. Interfaces & integrations

| Capability | Status | Known limits |
|---|---|---|
| MCP server — public tools with typed outputs | Shipped | Automated generation and drift checks from the canonical API spec are in progress |
| REST API | Shipped (spec refresh pending) | OpenAPI is published, but some current routes are not yet listed |
| Python SDK — `pip install synapse-layer` → `from synapse_layer import Synapse` | Shipped | Canonical sync client. The standalone `synapse-sdk-python` repository is legacy |
| Agent skill | Shipped (beta) | Official = maintained by the org; beta = stability/support level. Durable-content save policy |
| LangGraph checkpointer | Experimental | `put_writes` is a no-op in the MVP; reads are fail-open, writes fail-closed. Not for production |

## 8. Explicitly not claimed

- Zero-knowledge / end-to-end encryption — the service processes plaintext in memory
- Operator-blind encryption — false; the service decrypts server-side and processes plaintext in memory
- Formal differential privacy
- AI-initiated merge or deletion of content (policy-based TTL/GC may delete expired data per configured retention rules; the sweep may dismiss non-actionable suggestions — reversibility evolving)
- Certified LGPD/GDPR compliance — mechanisms shipped; propagation audit pending
- SOC 2 / HIPAA certification
- Published token-savings results
- Per-agent/category RBAC, SSO/Entra ID, BYOC

## 9. How to use this file

1. Every public claim must map to a row above.
2. If a capability is not Shipped, the README must say Gated, In progress, Experimental or Roadmap.
3. If a claim cannot be traced here, remove it or move it to the roadmap.
4. Operational evidence is recorded privately per release — never in this file.
