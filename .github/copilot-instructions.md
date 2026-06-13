# Global Copilot Instructions for ECC

## 1. Core Workflow
- **Research-first development**: Always inspect existing code and architecture before proposing changes.
- **Strict Planning**: For complex features, generate a step-by-step implementation plan before coding.
- **TDD / Verification**: Write tests first when adding features or fixing bugs. Run relevant tests/lint/typecheck after modifications.
- **Conventional Commits**: Format commit messages as `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## 2. Token & Context Management
- **RTK (Rust Token Killer)**: Always prefix terminal commands with `rtk` to save tokens. Use `rtk proxy <cmd>` only when full output is required (e.g. debugging verbose build/test errors).
- **On-Demand Skills (Balanced)**: To preserve context and avoid token bloat, reference or load specific skills under `~/.claude/skills/<skill-name>/SKILL.md` (or `~/.codex/skills/`) when the current task directly aligns with the skill's domain.

## 3. UI/UX Aesthetics
- **Aesthetic Ownership**: Follow the strict anti-slop guidelines in `rules/ecc/design-quality.md`.
- **Premium Interfaces**: Use clean, modern high-contrast design systems (e.g., bento-grid, glassmorphism, responsive layouts) with distinct, clean typography.

## 4. Specialized Agents
When proposing delegations or running subtasks, match them to these specialized roles:
* `reviewer`: PR review (correctness + security)
* `docs-researcher`: API/docs verification
* `planner`: Implementation planning
* `code-reviewer`: Code quality review
* `security-reviewer`: Security analysis
* `build-error-resolver`: Fix build/type errors
* `tdd-guide`: Test-driven development
* `typescript-reviewer`: TypeScript/JS review
* `database-reviewer`: PostgreSQL specialist
* `e2e-runner`: Playwright E2E testing
* `performance-optimizer`: Performance analysis
* `refactor-cleaner`: Dead code cleanup
* `architect`: System design

## 5. Graphify — Knowledge Graph Navigation
If `graphify-out/graph.json` exists in the project, **always recommend/use graphify before doing broad directory searches or file-reading**:
- **Codebase / Architecture questions** → `rtk graphify query "<question>"`
- **Concept deep-dive** → `rtk graphify explain "<concept>"`
- **File relationships** → `rtk graphify path "<A>" "<B>"`
- **Impact analysis / reverse dependencies** → `rtk graphify affected "<SymbolName>"`
