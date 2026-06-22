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

⚠️ GRAPHIFY WORKFLOW RULES:
CRITICAL: For any codebase structure/relationship questions, your FIRST tool call MUST be `rtk graphify query "<question>"`. Graphify-first is mandatory.

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, or inline scripts to explore.
- Use at most **20 Graphify calls** per question. After 20 calls, hard stop and synthesize.
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files identified by Graphify.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or a broad report is requested.
- If a tool is blocked, do not retry. Run `graphify update .` after code edits.
- Blocked Tool Recovery: Do not create one-off scratch scripts. Use scripts/inspect_conversation.py to debug.
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
