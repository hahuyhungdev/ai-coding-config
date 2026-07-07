---
name: codebase-design
description: Use when designing or refactoring module interfaces, improving architecture, finding deepening opportunities, deciding where a seam belongs, making code more testable, reducing shallow pass-through modules, or reviewing whether a module boundary gives callers leverage and maintainers locality.
---

# Codebase Design

Design deep modules: a lot of behavior behind a small interface, placed at a clean seam and testable through that interface.

## When to Use

Use this skill when reviewing or changing module interfaces, architecture seams, testability, adapter placement, or shallow pass-through layers. Do not use it for routine implementation work where the existing module shape is already clear.

## Vocabulary

Use these terms consistently:

- **Module:** anything with an interface and implementation. It can be a function, class, package, feature, route handler, or tier-spanning slice.
- **Interface:** everything a caller must know to use the module: types, invariants, ordering constraints, error modes, required config, and performance characteristics.
- **Implementation:** the code hidden behind the interface.
- **Seam:** the place where the interface lives and behavior can vary without editing callers.
- **Adapter:** a concrete implementation that satisfies an interface at a seam.
- **Depth:** how much useful behavior callers get per unit of interface they must learn.
- **Leverage:** payoff to callers when one interface unlocks many behaviors.
- **Locality:** payoff to maintainers when change, bugs, and verification concentrate in one place.

Avoid using "boundary" when you mean seam, and avoid treating a TypeScript `interface` declaration as the whole interface.

## Deep Module Heuristics

A module is deep when:

- callers learn a small, stable interface,
- complex decisions stay inside the implementation,
- tests can verify behavior through the same interface callers use,
- a fix inside the module benefits many callers.

A module is shallow when:

- the interface is nearly as complex as the implementation,
- it mostly forwards arguments,
- callers still need to understand internal sequencing,
- tests must reach past the interface to verify important behavior.

Use the deletion test: if deleting the module only moves complexity into callers, it was earning its keep. If deletion removes complexity, it was probably pass-through structure.

## Workflow

1. Inspect the current context and existing patterns before proposing new seams.
2. Identify the behavior that needs a home, not just the files that look messy.
3. Name the candidate module and its interface.
4. Write a caller-facing usage sketch before implementation details.
5. State what complexity moves behind the interface.
6. Classify adapters only when at least two real variants exist or are directly required.
7. Define how the module is tested through its interface.
8. Compare against one simpler alternative before committing to the shape.

Do not create a seam for speculative future variants. One adapter means a hypothetical seam; two adapters means a real one.

## Design Review Checklist

For each proposed module, answer:

- What must a caller know?
- What invariants does the module enforce?
- What errors can cross the interface?
- What dependency is injected instead of constructed internally?
- Which behavior becomes easier to test?
- Which existing callers become simpler?
- What would make this module shallow?

Prefer replacing shallow layers with a deeper module over stacking another layer on top.
