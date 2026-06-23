#!/usr/bin/env python3
import os
from pathlib import Path

# Paths
REPO_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_DIR / "templates" / "base_instructions.md"

# Targets definition
TARGETS = {
    "claude": {
        "dest_path": REPO_DIR / "claude" / "CLAUDE.md",
        "variables": {
            "TITLE": "# Global Claude Code Instructions",
            "GLOBAL_PATH": "~/.claude",
            "SKILLS_PATH": "~/.claude/skills/<skill-name>/SKILL.md",
            "AGENT_PATH": "~/.claude/agents/",
            "AGENT_DELEGATION_DESC": "using available subagent/delegation tooling when supported",
            "RTK_REFERENCE": "",
            "BROWSER_AUTOMATION_RULE": "Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel when configured and available; otherwise, run tests via CLI test runners. Always ensure manual screenshots or browser artifacts are directed to `.playwright-mcp/` or `scratch/` directories (and never to the repository root).",
        },
        "extra_middle": "\n@RTK.md\n\nWhen the user types `/graphify`, invoke the `skill` tool with `skill: \"graphify\"` before doing anything else.\n",
        "include_graphify": True,
        "graphify_header": "",
        "suffix": "\n## Custom Test Rules Added\n",
    },
    "codex": {
        "dest_path": REPO_DIR / "codex" / "AGENTS.md",
        "variables": {
            "TITLE": "# ECC for Codex CLI",
            "GLOBAL_PATH": "~/.codex",
            "SKILLS_PATH": "~/.codex/skills/<skill-name>/SKILL.md",
            "AGENT_PATH": "~/.codex/agents/",
            "AGENT_DELEGATION_DESC": "using the `/agent` command or available subagent/delegation tooling when supported",
            "RTK_REFERENCE": " See `~/.codex/RTK.md` for reference.",
            "BROWSER_AUTOMATION_RULE": "Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel when configured and available; otherwise, run tests via CLI test runners.",
        },
        "extra_middle": "\nWhen the user types `/graphify`, invoke the `skill` tool with `skill: \"graphify\"` before doing anything else.\n",
        "include_graphify": True,
        "graphify_header": "",
        "suffix": "",
    },
    "gemini": {
        "dest_path": REPO_DIR / "gemini" / "ANTIGRAVITY.md",
        "variables": {
            "TITLE": "# Global Antigravity CLI Instructions",
            "GLOBAL_PATH": "~/.gemini/config",
            "SKILLS_PATH": "~/.gemini/config/skills/<skill-name>/SKILL.md",
            "AGENT_PATH": "~/.gemini/config/agents/",
            "AGENT_DELEGATION_DESC": "using available subagent/delegation tooling when supported",
            "RTK_REFERENCE": "",
            "BROWSER_AUTOMATION_RULE": "Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel when configured and available; otherwise, run tests via CLI test runners.",
        },
        "extra_middle": "",
        "include_graphify": True,
        "graphify_header": "",
        "suffix": "",
    },
    "github-copilot": {
        "dest_path": REPO_DIR / ".github" / "copilot-instructions.md",
        "variables": {
            "TITLE": "# Global Copilot Instructions for ECC",
            "GLOBAL_PATH": "~/.claude",
            "SKILLS_PATH": "~/.claude/skills/<skill-name>/SKILL.md (or ~/.codex/skills/)",
            "AGENT_PATH": "~/.claude/agents/ (or ~/.codex/agents/)",
            "AGENT_DELEGATION_DESC": "using the `/agent` command",
            "RTK_REFERENCE": "",
            "BROWSER_AUTOMATION_RULE": "Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel.",
        },
        "extra_middle": "",
        "include_graphify": True,
        "graphify_header": "## 6. Graphify — Knowledge Graph Navigation\n",
        "suffix": "",
    },
    "ide-copilot": {
        "dest_path": REPO_DIR / "copilot" / "copilot-instructions.md",
        "variables": {
            "TITLE": "# Global Copilot Instructions for ECC",
            "GLOBAL_PATH": "~/.claude",
            "SKILLS_PATH": "~/.claude/skills/<skill-name>/SKILL.md (or ~/.codex/skills/)",
            "AGENT_PATH": "~/.claude/agents/ (or ~/.codex/agents/)",
            "AGENT_DELEGATION_DESC": "using the `/agent` command",
            "RTK_REFERENCE": "",
            "BROWSER_AUTOMATION_RULE": "Run E2E tests and visual verification using Playwright MCP on the `msedge` (Microsoft Edge) channel.",
        },
        "extra_middle": "",
        "include_graphify": False,
        "graphify_header": "## 6. Graphify — Knowledge Graph Navigation\n",
        "suffix": "",
    },
}

GRAPHIFY_RULES = """<!-- ai-coding-config:graphify-start -->
## graphify

⚠️ GRAPHIFY WORKFLOW RULES (MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION):

**CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query "<question>"`. Do NOT use `list_dir`, `grep_search`, `find`, `cat`, or `view_file` as your first exploration step. Graphify-first is non-negotiable.**

Commands:
- Architecture questions → `rtk graphify query "question"`
- Code relationships → `rtk graphify path "A" "B"`
- Deep-dive concepts → `rtk graphify explain "concept"`
- Impact analysis / reverse dependencies → `rtk graphify affected "SymbolName"`

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, sed, awk, or inline scripts to explore.
- Use at most **20 Graphify calls** total per question. After 20 calls, hard stop and synthesize from available context.
- **Focus queries on specific symbols** — prefer `graphify query "what does X do"` over `graphify query "explain the codebase"`.
- **Synthesize from Graphify context only.** Answer based on what Graphify returns. Do not supplement with direct file reads for exploration.
- **If a tool call is blocked, do not retry.** Proceed and answer using the available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- Do not manually read or parse graphify-out/graph.json; it is an internal artifact. Use the graphify CLI (`rtk graphify query/path/explain/affected`) instead. Existence probes such as `test -f graphify-out/graph.json` are acceptable.
- Explicit docs files may be read as user-provided context before Graphify. Mapping those docs to source code, routes, components, or architecture still requires Graphify first.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.

Post-Discovery Reads (exceptions):
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files already identified by Graphify.
- You MUST have run at least one Graphify query before reading source files directly.
- When reading after discovery, state your justification (e.g., "Reading for editing" or "Verifying config structure").
- After modifying code, run `graphify update .`.

Blocked Tool Recovery:
- If a hook blocks a direct read/search or inline script, do not retry the same blocked call or attempt an equivalent bypass.
- Do not spawn subagents or fresh sessions to bypass blocked tools, Graphify quota, or current session scope restrictions.
- Do not create one-off scratch scripts to inspect facts that a project diagnostic already covers.
- For conversation log debugging in this repo, use `rtk python3 scripts/inspect_conversation.py <conversation_id> --step-index <n> --keyword "<text>"`; add `--compare-logs` when comparing compact vs full transcripts.
- When debugging truncation, measure full content length and keyword presence; do not use substring-only previews as evidence.
<!-- ai-coding-config:graphify-end -->"""

EMPTY_GRAPHIFY_BLOCK = """<!-- ai-coding-config:graphify-start -->
<!-- ai-coding-config:graphify-end -->"""

HEADER_WARNING = "<!-- GENERATED FILE - DO NOT EDIT DIRECTLY. EDIT templates/base_instructions.md INSTEAD -->\n"


def compile_instructions():
    print(f"Reading base template from {TEMPLATE_PATH}...")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template_content = f.read()

    for name, target in TARGETS.items():
        dest = target["dest_path"]
        print(f"Compiling instructions for {name} -> {dest}...")

        # Perform variable replacements
        content = template_content
        for key, value in target["variables"].items():
            content = content.replace(f"{{{{{key}}}}}", value)

        # Append extra middle logic
        if target["extra_middle"]:
            content += target["extra_middle"]

        # Append graphify block
        if target["graphify_header"]:
            content += "\n" + target["graphify_header"]

        if target["include_graphify"]:
            content += "\n" + GRAPHIFY_RULES + "\n"
        else:
            content += "\n" + EMPTY_GRAPHIFY_BLOCK + "\n"

        # Append suffix
        if target["suffix"]:
            content += target["suffix"]

        # Write output file with generated header warning
        os.makedirs(dest.parent, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(HEADER_WARNING + content)

    print("Compilation complete!")


if __name__ == "__main__":
    compile_instructions()
