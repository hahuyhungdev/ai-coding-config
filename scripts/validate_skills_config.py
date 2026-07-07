#!/usr/bin/env python3
"""Validate the repository skill registry and SKILL.md frontmatter."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BROAD_KEYWORDS = {
    "component",
    "components",
    "state",
    "refactor",
    "refactoring",
    "design",
    "api",
    "query",
    "testing",
}
HEAVY_DEPENDENCIES = {"frontend-scan"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("skills config must be a JSON object")
    return data


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}

    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            cycles.append(visiting[visiting.index(name) :] + [name])
            return
        if name in visited:
            return

        visiting.append(name)
        for dep in graph.get(name, []):
            if dep in graph:
                visit(dep)
        visiting.pop()
        visited.add(name)

    for skill_name in graph:
        visit(skill_name)

    return cycles


def validate(config_path: Path) -> tuple[list[str], list[str]]:
    config = load_json(config_path)
    config_root = config_path.parent
    skills = config.get("skills")
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(skills, list):
        return ["skills must be an array"], warnings

    names: set[str] = set()
    first_seen: dict[str, dict[str, Any]] = {}

    for raw_skill in skills:
        if not isinstance(raw_skill, dict):
            errors.append("skill entries must be objects")
            continue

        name = raw_skill.get("name")
        rel_path = raw_skill.get("path")
        if not isinstance(name, str) or not name:
            errors.append("skill missing name")
            continue
        if not NAME_RE.match(name):
            errors.append(f"invalid skill name: {name}")
        if name in names:
            errors.append(f"duplicate skill name: {name}")
        else:
            names.add(name)
            first_seen[name] = raw_skill

        if not isinstance(rel_path, str) or not rel_path:
            errors.append(f"skill missing path: {name}")
            continue

        skill_path = config_root / rel_path
        if not skill_path.exists():
            errors.append(f"missing skill path: {name} -> {rel_path}")
            continue

        frontmatter = parse_frontmatter(skill_path)
        fm_name = frontmatter.get("name")
        if fm_name != name:
            errors.append(f"frontmatter name mismatch: {name}")
        description = frontmatter.get("description")
        if not description:
            errors.append(f"missing frontmatter description: {name}")
        elif len(description) > 1024:
            errors.append(f"frontmatter description too long: {name}")

        triggers = raw_skill.get("triggers", {})
        if isinstance(triggers, dict):
            for keyword in triggers.get("keywords", []) or []:
                if isinstance(keyword, str) and keyword.lower() in BROAD_KEYWORDS:
                    warnings.append(f"warning: broad trigger keyword in {name}: {keyword}")

        for dep in raw_skill.get("dependencies", []) or []:
            if dep in HEAVY_DEPENDENCIES:
                warnings.append(f"warning: broad dependency in {name} -> {dep}")

    for name, skill in first_seen.items():
        deps = skill.get("dependencies", []) or []
        if not isinstance(deps, list):
            errors.append(f"dependencies must be an array: {name}")
            continue
        for dep in deps:
            if not isinstance(dep, str):
                errors.append(f"dependency must be a string: {name}")
            elif dep not in names:
                errors.append(f"missing dependency: {name} -> {dep}")

    graph = {
        name: [
            dep
            for dep in (skill.get("dependencies", []) or [])
            if isinstance(dep, str) and dep in names
        ]
        for name, skill in first_seen.items()
    }
    for cycle in detect_cycles(graph):
        errors.append("dependency cycle: " + " -> ".join(cycle))

    return errors, warnings


def main(argv: list[str]) -> int:
    config_path = Path(argv[1]) if len(argv) > 1 else Path("skills.json")
    errors, warnings = validate(config_path.resolve())

    for warning in warnings:
        print(warning)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"skills config OK: {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
