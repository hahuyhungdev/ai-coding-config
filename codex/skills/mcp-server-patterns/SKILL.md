---
name: mcp-server-patterns
description: Build MCP servers with Node/TypeScript SDK — tools, resources, prompts, Zod validation, stdio vs Streamable HTTP. Use when implementing MCP servers or debugging transport issues.
---

# MCP Server Patterns

## Core Concepts

- **Tools**: Actions the model can invoke (search, run command)
- **Resources**: Read-only data the model can fetch (file contents, API responses)
- **Prompts**: Reusable parameterized prompt templates
- **Transport**: stdio for local clients, Streamable HTTP for remote

## Setup

```bash
npm install @modelcontextprotocol/sdk zod
```

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js"
import { z } from "zod"

const server = new McpServer({ name: "my-server", version: "1.0.0" })
```

## Register Tools

```typescript
server.tool(
  "search",
  "Search for items",
  { query: z.string(), limit: z.number().optional() },
  async ({ query, limit }) => {
    const results = await search(query, limit ?? 10)
    return { content: [{ type: "text", text: JSON.stringify(results) }] }
  }
)
```

## Register Resources

```typescript
server.resource(
  "config",
  "config://app",
  async (uri) => ({
    contents: [{ uri: uri.href, text: JSON.stringify(config) }]
  })
)
```

## Transport: stdio (Local)

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
const transport = new StdioServerTransport()
await server.connect(transport)
```

## Transport: Streamable HTTP (Remote)

For Cursor, cloud, or remote clients. Legacy HTTP/SSE only for backward compatibility.

## Best Practices

- Schema first: define input schemas for every tool
- Return structured errors, not raw stack traces
- Prefer idempotent tools for safe retries
- Rate limit tools that call external APIs
- Pin SDK version in package.json
- Keep server logic independent of transport
