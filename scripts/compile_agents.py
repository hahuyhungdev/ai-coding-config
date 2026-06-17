#!/usr/bin/env python3
import sys
import os
import re
import shutil
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SRC_AGENTS_DIR = REPO_DIR / "agents"

HOME_DIR = Path.home()
CLAUDE_AGENTS_DIR = HOME_DIR / ".claude" / "agents"
CODEX_AGENTS_DIR = HOME_DIR / ".codex" / "agents"
AGY_AGENTS_DIR = HOME_DIR / ".gemini" / "config" / "agents"


def parse_frontmatter(text):
    lines = text.splitlines()
    meta = {}
    codex_meta = None
    in_codex = False

    for line in lines:
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue

        if in_codex:
            if line.startswith(" ") or line.startswith("\t"):
                indent_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", trimmed)
                if indent_match:
                    if codex_meta is None:
                        codex_meta = {}
                    key = indent_match.group(1).strip()
                    val = indent_match.group(2).strip().strip("'\"")
                    codex_meta[key] = val
                    continue
            else:
                in_codex = False

        match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", trimmed)
        if match:
            key = match.group(1).strip()
            val = match.group(2).strip()
            if key == "codex":
                in_codex = True
            else:
                meta[key] = val.strip("'\"")

    if codex_meta is not None:
        meta["codex"] = codex_meta
    return meta


def ensure_clean_dir(directory: Path):
    try:
        if directory.is_symlink():
            directory.unlink()
        elif directory.is_dir():
            for item in directory.iterdir():
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            return
        elif directory.exists():
            directory.unlink()
    except Exception:
        pass
    directory.mkdir(parents=True, exist_ok=True)


def main():
    args = sys.argv[1:]
    compile_claude = False
    compile_codex = False
    compile_agy = False

    if not args or "--all" in args:
        compile_claude = True
        compile_codex = True
        compile_agy = True
    else:
        if "--claude" in args:
            compile_claude = True
        if "--codex" in args:
            compile_codex = True
        if "--agy" in args:
            compile_agy = True

    try:
        if compile_claude:
            ensure_clean_dir(CLAUDE_AGENTS_DIR)
            print(f"Writing Claude agents directly to: {CLAUDE_AGENTS_DIR}")
        if compile_codex:
            ensure_clean_dir(CODEX_AGENTS_DIR)
            print(f"Writing Codex agents directly to: {CODEX_AGENTS_DIR}")
        if compile_agy:
            ensure_clean_dir(AGY_AGENTS_DIR)
            print(f"Writing agy agents directly to: {AGY_AGENTS_DIR}")

        if not SRC_AGENTS_DIR.exists():
            print(f"Source agents directory {SRC_AGENTS_DIR} does not exist.")
            return

        files = sorted([f for f in SRC_AGENTS_DIR.iterdir() if f.is_file() and f.name.endswith(".md")])
        print(f"Found {len(files)} agent source files. Starting compilation...")

        for file_path in files:
            content = file_path.read_text(encoding="utf-8")
            name = file_path.stem

            match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$", content)
            if not match:
                print(f"[WARN] Skipping {file_path.name} due to missing frontmatter")
                continue

            frontmatter_text = match.group(1)
            body = match.group(2)
            meta = parse_frontmatter(frontmatter_text)

            # 1. Compile Claude Agent (Markdown)
            if compile_claude:
                claude_frontmatter = "---\n"
                for key, value in meta.items():
                    if key != "codex":
                        claude_frontmatter += f"{key}: {value}\n"
                claude_frontmatter += "---\n"
                claude_content = claude_frontmatter + body
                (CLAUDE_AGENTS_DIR / f"{name}.md").write_text(claude_content, encoding="utf-8")

            # 2. Compile agy Agent (Markdown)
            if compile_agy:
                agy_frontmatter = "---\n"
                for key, value in meta.items():
                    if key != "codex":
                        agy_frontmatter += f"{key}: {value}\n"
                agy_frontmatter += "---\n"
                agy_content = agy_frontmatter + body
                (AGY_AGENTS_DIR / f"{name}.md").write_text(agy_content, encoding="utf-8")

            # 3. Compile Codex Agent (TOML)
            if compile_codex:
                codex_model = "gpt-5.5"
                codex_reasoning = "high"
                codex_sandbox = "workspace-write"

                if meta.get("model") == "sonnet":
                    codex_reasoning = "medium"
                elif meta.get("model") == "haiku":
                    codex_reasoning = "low"
                    codex_sandbox = "read-only"

                codex_meta = meta.get("codex")
                if codex_meta:
                    if "model" in codex_meta:
                        codex_model = codex_meta["model"]
                    if "model_reasoning_effort" in codex_meta:
                        codex_reasoning = codex_meta["model_reasoning_effort"]
                    if "sandbox_mode" in codex_meta:
                        codex_sandbox = codex_meta["sandbox_mode"]

                description = meta.get("description", "")
                toml_content = f'model = "{codex_model}"\n'
                toml_content += f'model_reasoning_effort = "{codex_reasoning}"\n'
                toml_content += f'sandbox_mode = "{codex_sandbox}"\n\n'
                toml_content += f'description = "{description}"\n\n'
                toml_content += f'developer_instructions = """\n{body.strip()}\n"""\n'

                (CODEX_AGENTS_DIR / f"{name}.toml").write_text(toml_content, encoding="utf-8")

        print("Agent compilation complete!")
    except Exception as err:
        print(f"Compilation failed: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
