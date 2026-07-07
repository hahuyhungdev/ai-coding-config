#!/usr/bin/env python3
"""Run deterministic trigger evals against skills.json."""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def file_extension(path: str) -> str:
    name = Path(path).name
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[1]


def file_trigger_matches(trigger: str, path: str) -> bool:
    normalized_trigger = trigger.lower().lstrip(".")
    name = Path(path).name.lower()
    if any(marker in normalized_trigger for marker in ("*", "?", "[")):
        return fnmatch.fnmatch(name, normalized_trigger)
    return file_extension(path).lower() == normalized_trigger


def skill_matches(skill: dict[str, Any], query: str, files: list[str]) -> bool:
    triggers = skill.get("triggers", {})
    if not isinstance(triggers, dict):
        return False

    query_lower = query.lower()
    for keyword in triggers.get("keywords", []) or []:
        if isinstance(keyword, str) and keyword.lower() in query_lower:
            return True

    for pattern in triggers.get("pathPatterns", []) or []:
        if isinstance(pattern, str) and any(fnmatch.fnmatch(path, pattern) for path in files):
            return True

    file_triggers = [
        trigger
        for trigger in (triggers.get("fileExtensions", []) or [])
        if isinstance(trigger, str)
    ]
    if file_triggers and any(
        file_trigger_matches(trigger, path)
        for trigger in file_triggers
        for path in files
    ):
        return True

    return False


def expand_dependencies(matches: set[str], skills_by_name: dict[str, dict[str, Any]]) -> set[str]:
    expanded = set(matches)
    changed = True
    while changed:
        changed = False
        for name in list(expanded):
            for dep in skills_by_name.get(name, {}).get("dependencies", []) or []:
                if isinstance(dep, str) and dep not in expanded:
                    expanded.add(dep)
                    changed = True
    return expanded


def evaluate(config_path: Path, evals_path: Path) -> tuple[int, list[str]]:
    config = load_json(config_path)
    evals = load_json(evals_path)
    skills = config.get("skills", [])
    skills_by_name = {
        skill["name"]: skill
        for skill in skills
        if isinstance(skill, dict) and isinstance(skill.get("name"), str)
    }
    failures: list[str] = []

    for case in evals:
        name = case.get("name", "<unnamed>")
        query = case.get("query", "")
        files = case.get("files", []) or []
        expected = set(case.get("expect", []) or [])
        forbidden = set(case.get("forbid", []) or [])

        matches = {
            skill_name
            for skill_name, skill in skills_by_name.items()
            if skill_matches(skill, query, files)
        }
        actual = expand_dependencies(matches, skills_by_name)
        missing = expected - actual
        unexpected = forbidden & actual

        if missing or unexpected:
            details = []
            if missing:
                details.append("missing=" + ",".join(sorted(missing)))
            if unexpected:
                details.append("forbidden=" + ",".join(sorted(unexpected)))
            details.append("actual=" + ",".join(sorted(actual)))
            failures.append(f"{name}: " + " ".join(details))

    return len(evals) - len(failures), failures


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="skills.json")
    parser.add_argument("--evals", default="evals/skill-trigger-evals.json")
    args = parser.parse_args(argv[1:])

    passed, failures = evaluate(Path(args.config), Path(args.evals))
    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1

    print(f"skill trigger evals OK: {passed} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
