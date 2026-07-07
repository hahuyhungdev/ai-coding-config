---
name: prototype-spike
description: Use for throwaway prototypes or spikes that answer a design question before production work, especially explicit requests to prototype, compare UI variations, explore state models, test interaction feel, or try a few workflow/design directions.
---

# Prototype Spike

A prototype is throwaway code that answers one question. It is not production implementation.

## When to Use

Use this skill when a quick prototype can answer a design, state-model, interaction, or workflow question before production implementation. Do not use it for committed feature work where the target behavior is already known.

## Pick The Question

Start by naming the question the prototype must answer.

Common branches:

- **Logic/state model:** build a tiny terminal or local harness that exposes state after each action.
- **UI direction:** create a small route/page/artifact with 2-3 distinct variants that can be compared quickly.
- **Workflow feel:** simulate the shortest realistic path a user would take, then inspect friction.

If the prompt is vague and the user is not available, choose the branch that matches the surrounding code and state the assumption.

## Rules

- Mark files clearly as prototype/spike if they enter the repo.
- Keep the prototype close to the relevant module or page, following existing routing/build conventions.
- Provide one command or URL to run it.
- Use in-memory state unless persistence is the question.
- Skip production polish, broad error handling, durable abstractions, and unrelated tests.
- Surface the relevant state or differences visibly after each interaction.
- Delete the prototype or fold the validated decision into real code when done.

## UI Prototype Constraints

For UI direction, make variants meaningfully different:

- layout density,
- information hierarchy,
- interaction model,
- visual tone,
- responsive behavior.

Do not create several versions of the same generic gradient/card template. Each variant must answer a real tradeoff.

Before turning any variant into production code, run the normal frontend verification path for the real implementation, not the throwaway prototype.

## Completion

Keep only the answer:

- the question,
- the tested variants or state cases,
- what worked,
- what did not,
- what should be implemented or avoided next.
