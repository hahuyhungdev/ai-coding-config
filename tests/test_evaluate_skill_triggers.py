import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "scripts" / "evaluate_skill_triggers.py"


def test_evaluator_matches_keywords_paths_and_dependencies(tmp_path: Path) -> None:
    config_path = tmp_path / "skills.json"
    evals_path = tmp_path / "evals.json"
    config_path.write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "name": "react-pattern",
                        "path": "skills/react-pattern/SKILL.md",
                        "triggers": {"keywords": ["compound component"]},
                    },
                    {
                        "name": "next-best-practices",
                        "path": "skills/next-best-practices/SKILL.md",
                        "triggers": {"pathPatterns": ["**/app/**"]},
                        "dependencies": ["react-pattern"],
                    },
                    {
                        "name": "documentation-lookup",
                        "path": "skills/documentation-lookup/SKILL.md",
                        "triggers": {"keywords": ["official docs"]},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    evals_path.write_text(
        json.dumps(
            [
                {
                    "name": "react-positive",
                    "query": "Refactor this into a compound component",
                    "files": [],
                    "expect": ["react-pattern"],
                },
                {
                    "name": "next-path-dep",
                    "query": "Fix this route",
                    "files": ["src/app/dashboard/page.tsx"],
                    "expect": ["next-best-practices", "react-pattern"],
                },
                {
                    "name": "docs-positive",
                    "query": "Check official docs for this API",
                    "files": [],
                    "expect": ["documentation-lookup"],
                },
                {
                    "name": "negative",
                    "query": "Rename this variable",
                    "files": ["src/utils/name.ts"],
                    "expect": [],
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(EVALUATOR), "--config", str(config_path), "--evals", str(evals_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skill trigger evals OK: 4 passed" in result.stdout


def test_evaluator_matches_wildcard_file_extension_patterns(tmp_path: Path) -> None:
    config_path = tmp_path / "skills.json"
    evals_path = tmp_path / "evals.json"
    config_path.write_text(
        json.dumps(
            {
                "skills": [
                    {
                        "name": "quality-gate",
                        "path": "skills/quality-gate/SKILL.md",
                        "triggers": {"fileExtensions": ["test_*.py", "*_test.go"]},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    evals_path.write_text(
        json.dumps(
            [
                {
                    "name": "python-wildcard",
                    "query": "Add test coverage",
                    "files": ["tests/test_orders.py"],
                    "expect": ["quality-gate"],
                },
                {
                    "name": "go-wildcard",
                    "query": "Add test coverage",
                    "files": ["internal/orders/order_test.go"],
                    "expect": ["quality-gate"],
                },
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(EVALUATOR), "--config", str(config_path), "--evals", str(evals_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skill trigger evals OK: 2 passed" in result.stdout
