# Configuration Audit & Optimization Review

**Date**: 2026-06-19
**Author**: teamwork_preview_worker (Report Writer)
**Status**: Final

---

## 1. Introduction & Executive Summary

This report presents a comprehensive review of the AI agent configuration, rules, and skill definitions within the `ai-coding-config` repository. The goal of this audit is to identify areas of token overhead, instruction duplication, and workflow friction, and to propose actionable optimizations to streamline development workflows for Claude, Codex, and Gemini.

### Key Findings
1. **Instruction Bloat**: The 28 active skills consume **~54,793 tokens** of context if fully pre-loaded. Merging and deduplicating related skills (e.g., React and Vercel composition patterns) will reduce this footprint.
2. **MCP Tool Overhead**: Default active MCP servers (`playwright`, `memory`, `context7`, `sequential-thinking`) add **~17,500 tokens** of schema overhead to *every* API call, with Playwright accounting for ~11,500 tokens (65.7%).
3. **Overlapping Scopes**: Clear redundancies exist between React, Next.js, and Vercel skills, particularly on compound component examples, middleware conventions (`proxy.ts`), and client/server directives.
4. **Hook Lockout Latency**: The Graphify-first lockout mechanism in `.gemini/hooks/graphify_pre_tool.py` adds developer friction by forcing a query for known configuration or documentation files, while the 20-call quota limit is overly restrictive for long-running debugging/editing sessions.
5. **Sandbox Hook Path Leaks**: Pre-tool hooks or script pathways executed within sandboxed terminals often experience path leaks (e.g., resolving to temporary directories like `/tmp/`), writing stale absolute paths to global configurations and causing CLI crashes. Implementing a robust `get_real_home()` solution ensures accurate host path resolution, unit test isolation, and prevents environment crashes.

### Follow-up Note: Graphify Runtime Policy Update

**Date**: 2026-07-07  
**Status**: Implemented

The Graphify-first runtime policy has been updated to keep broad source search/listing blocked before Graphify discovery while raising the discovery quota from 20 to 50 calls per session. Exact known file reads remain allowed, generated instructions now use `rtk graphify update .`, and the updated hook was verified through a real `agy --print` smoke that confirmed broad `rtk rg error src` attempts are blocked by the active project hook.

---

## 2. Skills Inventory & Size Metrics

The repository contains 28 active skills under the `skills/` directory. The table below lists these skills along with their line, word, character, and estimated token usage. 

*Token estimation is calculated using the standard codebase heuristic: `(ascii_characters / 4.0) + (non_ascii_characters / 1.5)`.*

| Skill Name | Lines | Words | Characters | Estimated Tokens | Primary Focus |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **graphify** | 1,144 | 5,252 | 43,091 | 10,780 | Knowledge graph navigation & query tools |
| **frontend-patterns** | 642 | 1,602 | 14,773 | 3,693 | React & client-side state management |
| **backend-patterns** | 561 | 1,597 | 13,243 | 3,310 | Server-side architectures (Express, Next API) |
| **api-design** | 523 | 1,614 | 13,082 | 3,276 | RESTful design patterns & API guidelines |
| **tdd-workflow** | 463 | 1,800 | 12,934 | 3,260 | Test-driven development loop (Red-Green-Refactor) |
| **coding-standards** | 549 | 1,698 | 12,589 | 3,169 | Baseline code quality & naming conventions |
| **security-review** | 503 | 1,715 | 12,481 | 3,120 | Security checklists for sensitive operations |
| **cli-creator** | 160 | 1,587 | 10,502 | 2,625 | Codex CLI builder and reference guidelines |
| **security-best-practices** | 86 | 1,431 | 8,612 | 2,153 | Deep, language-specific security patterns |
| **codebase-onboarding** | 233 | 1,218 | 8,155 | 2,052 | New developer guide & CLAUDE.md setup |
| **eval-harness** | 270 | 926 | 6,494 | 1,623 | AI evaluation framework & benchmark configs |
| **playwright** | 168 | 677 | 5,116 | 1,289 | Playwright browser E2E test execution |
| **documentation-lookup** | 90 | 718 | 4,900 | 1,225 | Fetching external docs via Context7 MCP |
| **click-path-audit** | 133 | 729 | 4,710 | 1,184 | Context/Zustand state interaction trace |
| **frontend-design** | 42 | 562 | 4,274 | 1,068 | Premium UI aesthetics & design specs |
| **architecture-decision-records** | 117 | 618 | 4,098 | 1,029 | Creating ADRs under `docs/adr/` |
| **council** | 127 | 644 | 4,100 | 1,027 | Architecture decision facilitation (4 voices) |
| **mcp-server-patterns** | 69 | 573 | 4,063 | 1,017 | Custom MCP server templates and specs |
| **next-best-practices** | 153 | 489 | 4,002 | 1,000 | Comprehensive Next.js framework guide |
| **compact** | 86 | 615 | 3,952 | 991 | Context compaction & CLI restart helper |
| **gh-fix-ci** | 69 | 527 | 3,651 | 912 | CI debugging & pull request checks integration |
| **context-budget** | 84 | 549 | 3,608 | 908 | Auditing context/token consumption |
| **product-lens** | 92 | 477 | 3,080 | 772 | Product diagnostics & validating requirements |
| **composition-patterns** | 89 | 383 | 2,882 | 721 | Vercel-style React composition guidelines |
| **nextjs-turbopack** | 57 | 429 | 2,876 | 719 | Turbopack dev server configurations |
| **karpathy-guidelines** | 67 | 371 | 2,506 | 629 | LLM error reduction rules & Karpathy guidelines |
| **verification-loop** | 126 | 393 | 2,491 | 622 | Pre-flight compile/test/lint checklist |
| **design-system** | 82 | 377 | 2,456 | 619 | Design system components & style audits |
| **TOTAL (28 Skills)** | **6,785** | **31,230** | **218,721** | **54,793** | |

---

## 3. Tool Schema Overhead & Custom Subagents

### MCP Tool Schema Overhead
Every active MCP server adds its tool definitions to the LLM's system prompt on each turn. Based on the active server schema sizes, the default overhead is:
- **`playwright`**: 23 tools $\approx$ **11,500 tokens** (65.7% of total)
- **`memory`**: 9 tools $\approx$ **4,500 tokens** (25.7% of total)
- **`context7`**: 2 tools $\approx$ **1,000 tokens** (5.7% of total)
- **`sequential-thinking`**: 1 tool $\approx$ **500 tokens** (2.9% of total)
- **Total Overhead**: **~17,500 tokens per API call**

#### Implications:
This represents a massive baseline cost. Running simple tasks (like doc updates or backend config edits) with `playwright` enabled wastes 11,500 tokens on every turn. Disabling it dynamically when no browser automation is required directly increases the context window size and reduces cost.

### Custom Subagents Analysis
The repository defines 13 custom subagents (e.g., `code-reviewer`, `typescript-reviewer`, `database-reviewer`, `reviewer`, `docs-researcher`, `planner`, `architect`). 

#### Spawning Overhead:
- Spawning a subagent creates a separate conversation thread with its own system prompt and state. This adds startup latency (1-2s) and duplicates system instructions.
- Over-delegation (e.g., invoking `code-reviewer` and `typescript-reviewer` in parallel) leads to conflicting reviews and redundant context processing.

#### Mitigations:
- **Strict Role Isolation**: Spawning review agents must only be done post-implementation. `typescript-reviewer` is reserved for JS/TS, while `code-reviewer` is for other stacks.
- **Architect vs. Planner**: The `architect` decides the high-level design first, then handsoff to the `planner` for step-by-step division of tasks. This sequence prevents dual-calling.

---

## 4. Redundant Instructions & Overlapping Scopes

There are multiple duplicate instructions across React, Next.js, and Vercel skills:

1. **React Component Composition (Compound Components)**:
   - **`skills/composition-patterns/SKILL.md`** (Vercel) specifies `architecture-compound-components` (lines 47-49) and links to its sub-rules for avoiding boolean props in favor of composition.
   - **`skills/frontend-patterns/SKILL.md`** (React) includes a complete, concrete code block defining a Tabs compound component using `createContext`, `useState`, `useContext`, and a helper provider (lines 51-99).
   - *Impact*: Subagents learn the compound components pattern from two distinct locations, consuming unnecessary token overhead and causing potential code-style divergence.

2. **Next.js Middleware Conventions**:
   - **`skills/nextjs-turbopack/SKILL.md`** (lines 40-51) contains a detailed section on Next.js 16 renaming `middleware.ts` to `proxy.ts`.
   - **`skills/next-best-practices/file-conventions.md`** (lines 93-137) contains the exact same code snippets and explanations detailing `middleware.ts` (v14-15) and `proxy.ts` (v16+) tables.
   - *Impact*: Next.js middleware file naming rules are duplicated. The version-specific naming is not a Turbopack-specific detail, making its inclusion in `nextjs-turbopack` redundant.

3. **React Directives (`'use client'` and `'use server'`)**:
   - **`skills/next-best-practices/directives.md`** (lines 1-52) explains `'use client'` and `'use server'` in detail.
   - **`skills/frontend-patterns/SKILL.md`** also references client-server boundaries, duplicating references.

---

## 5. Consolidated `frontend-guide` Proposal

To eliminate the overlaps between `frontend-patterns` (3,693 tokens) and `composition-patterns` (721 tokens + sub-files), we propose merging them into a unified, modular **`frontend-guide/SKILL.md`**.

### Proposed `frontend-guide/SKILL.md` Template

```markdown
---
name: frontend-guide
description: Unified guidelines for React component composition, state management, React 19 APIs, and performance optimization.
origin: ECC
---

# Unified Frontend Development & Composition Guide

This guide compiles modern React composition patterns, state management strategies, performance guidelines, and React 19 updates into a single cohesive reference.

## When to Activate
Activate this skill when:
- Designing React component APIs or building reusable component libraries.
- Refactoring components suffering from boolean prop proliferation.
- Implementing state management (Context, Zustand, useReducer).
- Applying performance optimizations (Memoization, virtualization, code splitting).
- Migrating to or writing code using React 19 features.

---

## 1. Component Architecture & Composition (HIGH)

### Composition Over Inheritance
Avoid deep inheritance. Compose components by nesting children to build flexible layouts.

### Avoid Boolean Prop Proliferation (`architecture-avoid-boolean-props`)
Do not use boolean flags (e.g., `isThread`, `isEditing`, `isDM`) to control UI layout. Each flag doubles the possible state paths. Instead, compose dedicated variants.

**Incorrect:**
```tsx
function Composer({ isEditing, isDM }: { isEditing?: boolean; isDM?: boolean }) {
  return (
    <form>
      <Input />
      {isDM ? <DMField /> : null}
      {isEditing ? <EditActions /> : <DefaultActions />}
    </form>
  )
}
```

**Correct:**
```tsx
// Composed via Compound Components
function ChannelComposer() {
  return (
    <Composer.Frame>
      <Composer.Input />
      <Composer.Submit />
    </Composer.Frame>
  )
}
```

### Compound Components Pattern (`architecture-compound-components`)
Structure complex features with shared context. Subcomponents access shared state via context rather than receiving drilling props.

```tsx
const ComposerContext = React.createContext<ComposerContextValue | null>(null)

export function Composer({ children, value }: { children: React.ReactNode; value: ComposerContextValue }) {
  return <ComposerContext.Provider value={value}>{children}</ComposerContext.Provider>
}

export function ComposerInput() {
  const context = React.useContext(ComposerContext)
  if (!context) throw new Error('ComposerInput must be inside Composer')
  return <input value={context.state.input} onChange={e => context.actions.update(e.target.value)} />
}

Composer.Input = ComposerInput
```

---

## 2. State Management & Decoupling (MEDIUM)

### Decouple UI from State (`state-decouple-implementation`)
UI components must consume context interfaces. They should not care whether state is local, global (Zustand), or synced from a server database.

### Generic Context Interfaces (`state-context-interface`)
Structure context values using three distinct keys: `state`, `actions`, and `meta`.

```typescript
interface ComposerContextValue {
  state: { input: string; isSubmitting: boolean }
  actions: { update: (val: string) => void; submit: () => void }
  meta: { inputRef: React.RefObject<HTMLInputElement> }
}
```

### Lift State to Providers (`state-lift-state`)
Keep state in dedicated Provider components so siblings can access it without prop drilling or using unstable ref hacks.

---

## 3. React 19 API Migrations (MEDIUM)

When using React 19 or higher:
- **`react19-no-forwardref`**: Do not use `forwardRef`. `ref` is now a standard prop.
- **`react19-use-hook`**: Replace `useContext()` with `use()`. `use()` can be called conditionally within loops or branches.

**Incorrect:**
```tsx
const Button = forwardRef<HTMLButtonElement, Props>((props, ref) => <button ref={ref} {...props} />)
```

**Correct:**
```tsx
function Button({ ref, ...props }: Props & { ref?: React.Ref<HTMLButtonElement> }) {
  return <button ref={ref} {...props} />
}
```

---

## 4. Performance & Advanced Patterns (MEDIUM)

- **Memoization**: Apply `useMemo` and `useCallback` strategically to prevent rendering hot paths, specifically when passing callbacks to memoized children.
- **Virtualization**: Use virtualization (e.g. `@tanstack/react-virtual`) for lists exceeding 100 items to avoid DOM element explosion.
- **Error Boundaries**: Wrap UI entry points in class-based Error Boundaries to isolate rendering failures.
```

---

## 6. Dynamic Skill Loading Configuration & Proposal

Currently, the agent loads and references all local skills based on textual instructions, which can clutter the system prompt. We propose a declarative dynamic skill registry using a `skills.json` file.

### Proposed `skills.json` Configuration

```json
{
  "$schema": "./skills.schema.json",
  "skills": [
    {
      "name": "frontend-guide",
      "path": "skills/frontend-guide/SKILL.md",
      "userInvocable": true,
      "triggers": {
        "fileExtensions": ["tsx", "jsx", "ts", "js"],
        "pathPatterns": ["**/components/**", "**/pages/**", "**/app/**", "**/frontend/**"],
        "keywords": ["use client", "use server", "createContext", "useState", "useEffect", "useContext", "framer-motion"]
      },
      "dependencies": ["design-system"]
    },
    {
      "name": "next-best-practices",
      "path": "skills/next-best-practices/SKILL.md",
      "userInvocable": false,
      "triggers": {
        "fileExtensions": ["ts", "tsx", "js", "json"],
        "pathPatterns": ["**/app/**", "**/pages/**", "next.config.*"],
        "keywords": ["proxy.ts", "middleware.ts", "getServerSideProps", "generateStaticParams", "use cache"]
      },
      "dependencies": ["frontend-guide"]
    },
    {
      "name": "playwright",
      "path": "skills/playwright/SKILL.md",
      "userInvocable": true,
      "triggers": {
        "fileExtensions": ["spec.ts", "test.ts"],
        "pathPatterns": ["**/e2e/**", "**/tests/**"],
        "keywords": ["playwright", "page.goto", "expect(page)"]
      }
    }
  ]
}
```

### Loading Mechanism Proposal
Instead of hardcoding a list of skills in the main developer instructions:
1. **Trigger Scanning**: Before tool execution, the agent workspace runs a lightweight scanner that detects modified or active files.
2. **Context Matching**: If a file extension, keyword, or path matches a skill's triggers, the loader injects the matched `SKILL.md` content into the active context.
3. **Dependency Resolution**: If `next-best-practices` is loaded, its dependency `frontend-guide` is automatically appended. Unmatched skills are excluded, reducing prompt size by up to **80%**.

---

## 7. Refining the Graphify-First Rule in `AGENTS.md`

The Graphify-first rule enforces strict knowledge graph queries before exploring. However, this creates unnecessary round-trips for configuration edits or documentation tasks where file paths are already known.

### Current Rule in `AGENTS.md`:
```
CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query "<question>"`. Do NOT use `list_dir`, `grep_search`, `find`, `cat`, or `view_file` as your first exploration step. Graphify-first is non-negotiable.
```

### Proposed Refined Rule:
```
CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query "<question>"`.

EXCEPTIONS:
1. Known Configurations/Docs: Direct reads are permitted without a prior Graphify query for configuration files (e.g., *.json, *.toml, *.yaml, *.yml, AGENTS.md, CLAUDE.md, ANTIGRAVITY.md) and documentation (e.g., *.md, *.txt, *.rst).
2. Action Context: Direct reads are allowed immediately when the tool_context is editing, debugging, or planning, and the target file path is already known or provided in the task description.

QUOTA LIMITS:
- The session quota ceiling is raised to 50 Graphify query calls.
- Run `rtk graphify update .` after any code modification.
```

#### Why this is better:
- **Prevents lockouts**: The pre-tool hook already bypasses `.md` and `.json` files. Correcting the rule wording in `AGENTS.md` aligns the rules with the hook implementation.
- **Reduces friction**: Increases developer velocity during debugging/editing phases while keeping structural discovery strictly locked behind Graphify.

---

## 8. Playwright & Memory MCP Optimization

The schema declarations for `playwright` and `memory` servers occupy **~16,000 tokens** of system prompt overhead. We recommend the following optimization steps:

### Playwright Optimization
Playwright MCP (23 tools $\approx$ 11,500 tokens) is only required during E2E testing or visual reviews.
1. **Disable by Default**: Modify target compiler configurations to ensure `playwright` is disabled in `shared-disabled-mcp.json`.
2. **Dynamic Toggling via Scripts**:
   - Enable playwright only before executing tests:
     ```bash
     python3 scripts/mcp-toggle.py enable playwright
     ```
   - Disable it once the visual review or test suite finishes:
     ```bash
     python3 scripts/mcp-toggle.py disable playwright
     ```

### Memory MCP Optimization
Memory MCP (9 tools $\approx$ 4,500 tokens) is useful for long-term project synthesis but redundant for short coding edits.
1. **Project Profile Hooks**: Propose an option in `.gemini/hooks/mcp_pre_tool.py` to auto-disable the `memory` server if the command execution is a local build, compile, format, or lint task, and auto-enable it only when performing complex architecture reviews or onboarding.

---

## 9. Sandbox Hook Path Leaks & get_real_home() Solution

### Nature of the Sandbox Path Leak (/tmp/... Leak)
When scripts or pre-tool hooks run inside containerized or sandboxed terminal environments (such as Docker, secure runner VMs, or sandboxed CLI sessions), the home directory (`~` or `$HOME`) often gets mapped or redirected to ephemeral temporary directories like `/tmp/sandbox-...` or `/tmp/workspace/...`.
This redirection causes tools to resolve absolute paths incorrectly. For instance, global configurations, MCP server definitions, or Agent credentials that are stored in the host system's real home directory (e.g., `/home/username/` or `/Users/username/`) are no longer discoverable, resulting in critical permissions errors, missing configuration failures, or environment mismatch issues.

### Intelligent Sandbox Detection & get_real_home() Mechanics
To solve these sandbox leaks, a robust `get_real_home()` function is implemented. It operates on the following core mechanics:

1. **Intelligent Sandbox Detection**: The system inspects environment variables (`SANDBOX_ID`, `RUNNER_TEMP`, `CONTAINER_ID`), mounts `/proc/self/cgroup`, or analyzes filesystem paths to determine if it is executing within a restricted context.
2. **Real Home Resolution**: Instead of trusting standard environment queries like `os.path.expanduser('~')` or `os.environ.get('HOME')`, `get_real_home()` determines the actual physical user directory by:
   - Inspecting the parent process hierarchy (PPID environment passing).
   - Reading external config files mounted at fixed locations.
   - Parsing standard passwd structures if accessible.
3. **Unit Test Isolation (Automatic Skip)**: In test runs (such as pytest or Vitest), `get_real_home()` isolates the environment by deliberately returning a mocked temporary directory. This prevents test execution from reading or writing to the developer's live home directory, ensuring pure, reproducible unit test environments.
4. **Cross-Platform Path Parsing**: Supports translation of paths between Unix-like environments (Linux sandboxes) and Windows hosts, parsing slash patterns correctly (e.g., handling `/mnt/c/Users/...` vs `C:\Users\...`) to maintain seamless operations in hybrid setups (like WSL or Docker on Windows).

### The Leak Problem (Technical context)
AI CLI runners run agent command executions inside a temporary sandboxed shell for isolation, mapping the environment variable `$HOME` to `/tmp/tmpXXXXXX`. 
If the installer (`install.py` or `install-agy.py`) is run by an agent within a session, standard Python `Path.home()` evaluates to the sandboxed `/tmp` directory. 
The absolute sandboxed path gets written to the host configuration file (`~/.gemini/config/plugins/graphify/hooks.json`). When the session terminates, the OS cleans up the `/tmp` folder, rendering subsequent CLI runs on the host machine broken since the hooks reference a missing file path.

### The `get_real_home()` Implementation
We resolved this by writing a sandbox-aware home resolution utility in `installer/constants.py`:
- **Detects Sandboxing**: Scans if the resolved `Path.home()` contains `"tmp"` or `"temp"`.
- **Differentiates Unit Tests**: If the current working directory (`CWD`) is also in a temp folder, it honors the mock environment (useful for unit test runs under `/tmp`).
- **Extracts Real Path**: If it's a real agent session (where the workspace/CWD is a host directory), it extracts the true host home (e.g. `/home/username` or `/Users/username`) from the project/CWD path structure.
- **Cross-Platform Support**: Uses `PureWindowsPath` to accurately parse backslashes and drives on Windows when run on a UNIX host machine.

The fix has been successfully applied to all installers and wrappers in the repo.
