# synapse-layer (TypeScript/JavaScript)

> MCP-Native Trust Infrastructure for AI Agents

Persistent, encrypted memory for AI agents. Store context in one agent, recall it from another — with Trust Quotient scoring to filter noise from signal. All memory is encrypted at rest with AES-256-GCM. Designed for LGPD/GDPR alignment.

[![npm](https://img.shields.io/npm/v/synapse-layer)](https://www.npmjs.com/package/synapse-layer)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](./LICENSE)

## Install

```bash
npm install synapse-layer
# or
yarn add synapse-layer
```

Requires Node.js 18+ (uses native `fetch`).

## Quickstart

```typescript
import { SynapseClient } from "synapse-layer";

const synapse = new SynapseClient({ apiKey: process.env.SYNAPSE_API_KEY! });

// Store — encrypted server-side with AES-256-GCM
const mem = await synapse.store({
  content: "User prefers dark mode.",
  agent: "settings-agent",
  memory_type: "preference",
});

// Recall — semantic search scored by Trust Quotient
const results = await synapse.recall({
  query: "display preferences",
  min_tq: 0.7,
});
```

## API Reference

### `new SynapseClient(options)`

| Option    | Type     | Default                        | Description           |
| --------- | -------- | ------------------------------ | --------------------- |
| `apiKey`  | `string` | —                              | Required. `sk_connect_…` |
| `baseUrl` | `string` | `https://synapselayer.org`     | API base URL          |
| `timeout` | `number` | `10000`                        | Request timeout (ms)  |

### `store(options): Promise<Memory>`

Store a memory. Content is encrypted at rest.

```typescript
await synapse.store({
  content: "User works at Acme Corp on ML pipelines.",
  agent: "onboarding-agent",
  memory_type: "profile",
  tags: ["company", "role"],
  metadata: { source: "intake-form" },
});
```

### `recall(options): Promise<Memory[]>`

Semantic recall with Trust Quotient filtering.

```typescript
const memories = await synapse.recall({
  query: "What does the user work on?",
  limit: 10,
  min_tq: 0.7,        // Only high-confidence memories
  agent: "support-agent",
  memory_type: "profile",
});
```

### `delete(memoryId): Promise<void>`

Permanently delete a memory. Irreversible.

```typescript
await synapse.delete("mem_abc123");
```

### `handover(options): Promise<HandoverResult>`

Secure Agent Handover (V2). Transfer context between agents with AES-256-GCM encryption and a single-use SHA-256 token.

```typescript
const result = await synapse.handover({
  from_agent: "sales-agent",
  to_agent: "support-agent",
  context: "Customer wants to upgrade to Pro plan.",
});
console.log("Handover token:", result.token);
```

### `health(): Promise<HealthResponse>`

```typescript
const status = await synapse.health();
console.log(status); // { status: "ok", version: "1.2.0", latency_ms: 12 }
```

## Trust Quotient

Every memory is scored with a Trust Quotient (TQ) from 0.0 to 1.0:

- **≥ 0.7** — High confidence. Use for critical decisions.
- **≥ 0.5** — General context. Good for background information.
- **< 0.3** — May contain noise. Consider filtering.

Filter in recall:

```typescript
const reliable = await synapse.recall({ query: "...", min_tq: 0.7 });
```

## Cross-Agent Memory

Memories are shared across agents within the same tenant. One agent stores, another recalls — with full audit trail.

```typescript
// Agent A stores
await synapse.store({ content: "...", agent: "agent-a", memory_type: "context" });

// Agent B recalls (different session, different agent)
const memories = await synapse.recall({ query: "...", min_tq: 0.6 });
// Returns memories from agent-a, scored by Trust Quotient
```

## Error Handling

```typescript
import { SynapseClient, AuthError, RateLimitError, NotFoundError } from "synapse-layer";

try {
  await synapse.recall({ query: "..." });
} catch (err) {
  if (err instanceof AuthError) {
    console.error("Invalid API key");
  } else if (err instanceof RateLimitError) {
    console.error("Too many requests — back off");
  } else if (err instanceof NotFoundError) {
    console.error("Memory not found");
  }
}
```

All errors extend `SynapseError` with `.statusCode` and `.code` properties. 5xx errors are automatically retried (3 attempts with exponential backoff). 4xx errors are thrown immediately.

## MCP Integration

Synapse Layer is MCP-native. For Claude Desktop, add to your MCP config:

```json
{
  "mcpServers": {
    "synapse-layer": {
      "command": "python",
      "args": ["-m", "synapse_layer.mcp"],
      "env": { "SYNAPSE_API_KEY": "sk_connect_your-key-here" }
    }
  }
}
```

See the [MCP documentation](https://synapselayer.org/docs) and the [Smithery listing](https://smithery.ai/server/synapselayer/synapse-protocol) for details.

## Contributing

Contributions welcome. Please open an issue first to discuss changes.

```bash
git clone https://github.com/SynapseLayer/synapse-layer.git
cd synapse-layer-ts
npm run build
npm run typecheck
```

## License

Apache-2.0 — see [LICENSE](./LICENSE).
