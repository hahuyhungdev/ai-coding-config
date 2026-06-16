---
name: context-budget
description: Audits context window consumption across agents, skills, MCP servers, and rules in this repo. Identifies bloat and redundant components. Use before adding new skills/MCPs, or when session feels slow.
metadata:
  origin: ECC (adapted)
---

# Context Budget

Analyze token overhead across every loaded component and surface actionable optimizations to reclaim context space.

## When to Use

- Before importing a new skill or MCP — check if there's room
- Session output quality is degrading
- You've recently added many skills/agents/MCPs
- User runs `/context-budget` or asks "do we have too many skills?"

## Inventory Targets (this repo)

### Skills (`skills/*/SKILL.md`)
- Count tokens per SKILL.md (lines × ~15 tokens/line as estimate)
- Flag: files > 400 lines → candidate for lazy-load
- Flag: two skills covering same domain (e.g. two "security" skills) → merge

### Agents (`~/.codex/agents/*.md` or local `agents/`)
- Count lines + frontmatter description length
- Flag: description > 30 words → bloated (loads into system prompt)
- Flag: agents not referenced in AGENTS.md → orphan

### MCP Servers (`.mcp.json` or `scripts/mcp-toggle.py list`)
- Count active servers and total tool count
- Estimate ~500 tokens per tool schema
- Flag: servers with > 20 tools → consider restricting tool list
- Flag: MCP that wraps simple CLI (`gh`, `git`, `npm`) → use shell command instead
- **Check**: run `python3 scripts/mcp-toggle.py list` to see enabled vs disabled state

### Rules / AGENTS.md
- Count lines in `AGENTS.md` and any `rules/` files
- Flag: combined > 300 lines → review for redundancy
- Check for overlapping guidance between `AGENTS.md` and individual skill SKILL.md files

## Classification

Sort every component into a bucket:

| Bucket | Criteria | Action |
|--------|----------|--------|
| **Always-on** | Loaded every session, referenced in AGENTS.md, backs active workflow | Keep |
| **On-demand** | Domain-specific, only needed for certain tasks | Mark as load-when-relevant |
| **Candidate for removal** | No command reference, overlapping content, never triggered in recent sessions | Remove or archive |

## Common Issues to Detect

- **Overlap between skills**: two skills giving similar guidance (e.g. `security-review` + `security-best-practices` — both exist in this repo, verify they don't repeat rules)
- **MCP over-provisioning**: optional MCPs left enabled when not needed (`postgres`, `sqlite`, `docker`) → disable with `python3 scripts/mcp-toggle.py disable <name>`
- **Dead agents**: agent files that exist but are never invoked
- **Bloated AGENTS.md**: rules that repeat what's already in individual SKILL.md files

## Output Format

Produce a table:

```
| Component | Type | Est. Tokens | Flag | Recommendation |
|-----------|------|-------------|------|----------------|
| frontend-design | skill | ~1200 | - | Keep (always-on) |
| security-review | skill | ~900 | overlap with security-best-practices | Merge or lazy-load |
| postgres MCP | mcp | ~3000 | disabled but registered | OK — disabled |
| ... | | | | |
```

Then produce a **token savings summary**:
```
Current estimated overhead: ~X tokens
After recommended changes:  ~Y tokens
Headroom gained:            ~Z tokens
```

## Adaptation Notes

- This repo uses `rtk` prefix for commands — factor RTK overhead (~minimal) into estimates
- MCP toggle managed via `python3 scripts/mcp-toggle.py` — always check status before recommending MCP removal
- `strategic-compact` skill already handles manual compaction — this skill focuses on structural audit, not mid-session compaction
