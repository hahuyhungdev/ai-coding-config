# Performance Optimization

## Model Selection Strategy

- **Haiku** — lightweight tasks, simple edits, docs
- **Sonnet** — main development, coding, multi-agent orchestration
- **Opus** — architectural decisions, complex reasoning, research

## Context Window Management

- Avoid the last 20% of context window during large refactoring
- Lower context-sensitivity tasks (single-file edits, docs) work in constrained windows

## Extended Thinking + Plan Mode

For complex tasks:
1. Ensure extended thinking is active
2. Enable Plan Mode
3. Run multiple critique rounds
4. Use split role sub-agents for diverse perspectives

## Build Troubleshooting

1. Use build-error-resolver agent
2. Analyze errors
3. Fix incrementally
4. Verify after each fix
