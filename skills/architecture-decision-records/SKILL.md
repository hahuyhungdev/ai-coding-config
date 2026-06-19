---
name: architecture-decision-records
description: Capture architectural decisions as structured ADR documents during coding sessions. Auto-detects decision moments, records context, alternatives considered, and rationale. Maintains docs/adr/ so future developers understand why the codebase is shaped the way it is.
metadata:
  origin: ECC (adapted)
---

# Architecture Decision Records

Capture architectural decisions as they happen. Instead of decisions living in Slack threads, PR comments, or someone's memory, this skill produces structured ADR documents that live alongside the code.

## When to Activate

- User explicitly says "let's record this decision" or "ADR this"
- User chooses between significant alternatives (framework, library, pattern, database, API design)
- User says "we decided to..." or "the reason we're doing X instead of Y is..."
- User asks "why did we choose X?" → read existing ADRs
- During planning phases when architectural trade-offs are discussed

**Do NOT activate for:** routine implementation choices, naming preferences, or aesthetic decisions. ADRs are for decisions with meaningful long-term consequences.

## ADR Format

Lightweight format by Michael Nygard, adapted for AI-assisted development:

```markdown
# ADR-NNNN: [Decision Title]

**Date**: YYYY-MM-DD
**Status**: proposed | accepted | deprecated | superseded by ADR-NNNN
**Deciders**: [who was involved]

## Context

What is the issue that we're seeing that is motivating this decision or change?

[2-5 sentences describing the situation, constraints, and forces at play]

## Decision

What is the change that we're proposing and/or doing?

[1-3 sentences stating the decision clearly]

## Alternatives Considered

### Alternative 1: [Name]
- **Pros**: [benefits]
- **Cons**: [drawbacks]
- **Why not**: [specific reason this was rejected]

### Alternative 2: [Name]
- **Pros**: [benefits]
- **Cons**: [drawbacks]
- **Why not**: [specific reason this was rejected]

## Consequences

### Positive
- [benefit 1]
- [benefit 2]

### Negative
- [trade-off 1]
- [trade-off 2]

### Risks
- [risk and mitigation]
```

## Workflow

### Capturing a New ADR

When a decision moment is detected:

1. **Initialize (first time only)** — if `docs/adr/` does not exist, ask the user for confirmation before creating it. Do NOT create files without explicit consent.
2. **Identify the decision** — extract the core architectural choice
3. **Gather context** — what problem prompted this? What constraints exist?
4. **Document alternatives** — what other options were considered? Why rejected?
5. **State consequences** — what are the trade-offs? What becomes easier/harder?
6. **Assign a number** — scan existing ADRs in `docs/adr/` and increment
7. **Confirm and write** — present the draft to the user for review. Only write to `docs/adr/NNNN-decision-title.md` after explicit approval. If the user declines, discard without writing.
8. **Update the index** — append to `docs/adr/README.md` index table

### Reading Existing ADRs

When user asks "why did we choose X?" or "what's the history of Y?":
1. Scan `docs/adr/` for relevant ADR titles
2. Read the matching file
3. Summarize: decision taken + the key reason + main trade-off accepted

### Updating an ADR

When a decision is reversed or superseded:
1. Update the original ADR status to `superseded by ADR-NNNN`
2. Write the new ADR referencing the old one

## ADR Index Format

Maintain `docs/adr/README.md` with:

```markdown
# Architecture Decision Records

| # | Title | Date | Status |
|---|-------|------|--------|
| 0001 | Use Playwright over Cypress for E2E | 2025-01-15 | accepted |
| 0002 | Graphify as primary codebase exploration tool | 2025-02-03 | accepted |
```

## Notes

- ADRs are **append-only by default** — update status, don't delete old records
- Keep ADRs short: 1 page max. If it's longer, the decision isn't clear yet
- The value is in "Alternatives Considered" — without it, the ADR is just a log entry
- This skill integrates naturally with `codebase-onboarding` — when onboarding to a new project, check `docs/adr/` first
