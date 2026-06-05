# Global Antigravity CLI Instructions

## Core workflow

- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **On-Demand Skills**: Only load and read skills under `~/.gemini/config/skills/<skill-name>/SKILL.md` when a task touches that domain. Do not load all skills into the context window at once.
- **Context Management**: Leverage the large Gemini context window, but proactively call the `strategic-compact` skill at logical milestones to summarize progress, keep latency fast, and prevent token bloat.

## UI/UX Leadership

- **Aesthetic Ownership**: Gemini is the primary owner for UI/UX visual design. Always follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`.
- **Premium Interfaces**: Use the `frontend-design` and `design-system` skills to build high-contrast, bento-grid, glassmorphic layouts with distinctive typography pairing and smooth hover transitions.

## MCP & Testing Integration

- **Database Verification**: Use the local `postgres` and `sqlite` MCP servers to inspect tables, verify migrations, and validate ORM queries directly rather than guessing.
- **Container Audit**: Check active services (Postgres, Redis, BullMQ) using the `docker` MCP server when debugging backends.
- **AWS Operations**: Access Lambda and Bedrock resources using the `aws` MCP server (run via `uvx`).
- **Browser Automation**: Run E2E tests and visual verification using Playwright MCP configured on the `msedge` (Microsoft Edge) channel.

## Coding Preferences

- Small, single-responsibility files over large monolithic files.
- Clear, descriptive naming over clever or complex abstractions.
- Prefer immutable data updates where idiomatic.
- Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.
