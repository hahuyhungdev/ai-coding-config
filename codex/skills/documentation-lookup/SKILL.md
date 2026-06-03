---
name: documentation-lookup
description: Fetch live library/framework docs via Context7 MCP. Use for setup questions, API references, code examples, or when user names a framework like React, Next.js, Prisma, Supabase.
---

# Documentation Lookup

Fetches up-to-date library documentation via Context7 MCP.

## Required MCP

Context7 MCP server must be configured.

## Tools

1. **resolve-library-id** — Convert library name to Context7 ID
2. **query-docs** — Fetch docs for a library ID

⚠️ Always call resolve-library-id FIRST. Never call query-docs directly.

## 4-Step Workflow

### 1. Resolve Library ID
Call `resolve-library-id` with library name and user's question.

### 2. Select Best Match
- Name match to user's request
- Benchmark score (max 100)
- Source reputation (High/Medium preferred)
- Version specificity if user mentions version

### 3. Fetch Documentation
Call `query-docs` with library ID and question.
Limit: max 3 calls per question.

### 4. Answer
Use fetched info, include code examples, cite library/version.

## Examples

**User**: "How do I set up middleware in Next.js?"
→ resolve-library-id("Next.js middleware setup")
→ query-docs("/vercel/next.js", "middleware setup")
→ Answer with code example from docs

**User**: "Prisma relation queries"
→ resolve-library-id("Prisma relations")
→ query-docs("/prisma/prisma", "relation queries include select")

## Best Practices

- Be specific with queries for better relevance
- Use version-specific IDs when user mentions version
- Prefer official sources over community forks
- Redact sensitive data before passing to Context7
