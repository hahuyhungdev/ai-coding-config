# Coding Style

## Immutability (CRITICAL)

ALWAYS create new objects, NEVER mutate existing ones.

## Core Principles

### KISS
- Prefer the simplest solution that works
- Avoid premature optimization
- Optimize for clarity over cleverness

### DRY
- Extract repeated logic into shared functions
- Introduce abstractions when repetition is real, not speculative

### YAGNI
- Don't build features before they are needed
- Start simple, refactor when pressure is real

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- 200-400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

- Handle errors explicitly at every level
- Provide user-friendly messages in UI
- Log detailed context on server side
- Never silently swallow errors

## Input Validation

- Validate all user input before processing
- Fail fast with clear error messages
- Never trust external data (API responses, user input)

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Proper error handling
- [ ] No hardcoded values
- [ ] No mutation (immutable patterns)
