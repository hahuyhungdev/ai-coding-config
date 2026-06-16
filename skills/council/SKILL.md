---
name: council
description: Convene four structured voices (Architect, Skeptic, Pragmatist, Critic) for ambiguous decisions with multiple credible paths. Use for go/no-go calls, tradeoff surfacing, or when conversational anchoring is a risk. NOT for code review or implementation planning.
metadata:
  origin: ECC (adapted)
---

# Council

Convene four advisors for decisions under genuine ambiguity. This is not code review, not architecture design, not planning — it is **structured disagreement before a high-stakes choice**.

## When to Use

- A decision has multiple credible paths and no obvious winner
- You need explicit tradeoff surfacing before committing
- The user asks for second opinions, dissent, or multiple perspectives
- Conversational anchoring is a real risk (agent keeps defaulting to one answer)
- A go/no-go call would benefit from adversarial challenge

**Examples of good council triggers:**
- monorepo vs polyrepo
- ship now vs hold for polish
- which MCP to enable vs use shell fallback
- whether to import a skill or write custom logic
- feature flag vs full rollout
- simplify scope vs keep strategic breadth

## When NOT to Use

| Instead of council | Use |
| --- | --- |
| Verifying whether output is correct | `verification-loop` skill |
| Breaking a feature into implementation steps | `planner` agent |
| Designing system architecture | `architect` agent |
| Reviewing code for bugs or security | `code-reviewer` or `security-review` skill |
| Straight factual questions | just answer directly |
| Obvious execution tasks | just do the task |

## The Four Voices

| Voice | Lens |
| --- | --- |
| **Architect** (in-context) | correctness, maintainability, long-term implications |
| **Skeptic** (subagent) | premise challenge, simplification, assumption breaking |
| **Pragmatist** (subagent) | shipping speed, user impact, operational reality |
| **Critic** (subagent) | edge cases, downside risk, failure modes |

The three external voices are launched as **fresh subagents** with only the question + compact context — no full conversation history. This is the anti-anchoring mechanism.

## Workflow

### 1. Extract the real question

Reduce to one explicit prompt:
- What are we deciding?
- What constraints matter?
- What counts as success?

If vague → ask one clarifying question before convening.

### 2. Gather only necessary context

If codebase-specific → collect relevant files/snippets, keep compact.
If strategic/general → skip repo snippets unless they change the answer.

### 3. Form Architect position first (in-context)

Before reading other voices, write down:
- Your initial position
- Three strongest reasons for it
- The main risk in your preferred path

Do this FIRST so synthesis doesn't mirror external voices.

### 4. Launch three voices in parallel

Each subagent receives:
- The decision question
- Compact context
- Their strict role (Skeptic / Pragmatist / Critic)
- **No conversation history**

Per this repo's AGENTS.md rules:
- Schedule a **liveness timer** before launching subagents
- Each subagent must call `send_message` back upon completion (success or failure)
- Do NOT poll — wait for notification

### 5. Synthesize

After all three report back:
- Compare against your Architect position
- Note: where do voices agree? Where do they diverge?
- Identify the **one or two decisive factors** that separate the paths

### 6. Decide and commit

Pick a path. State it clearly with the primary reason. Do not hedge into both directions. If genuinely too close to call, escalate to the user with a crisp summary.

## Output Format

```
## Council Session: [Decision title]

**Question**: [One sentence]
**Constraints**: [Bullets]

### Architect (initial position)
[Position + 3 reasons + main risk]

### Skeptic
[Challenge + what assumption they'd break]

### Pragmatist
[Shipping/impact lens + what they'd do today]

### Critic
[Failure modes + edge cases]

### Synthesis
[Where they agree / diverge]
[Decisive factors]

### Decision
**→ [Chosen path]**
Reason: [Primary reason]
Risk accepted: [The tradeoff you're accepting]
```
