import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_skills_config.py"


def write_skill(root: Path, name: str, description: str = "Use when testing skills.") -> str:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return f"skills/{name}/SKILL.md"


def write_config(root: Path, skills: list[dict]) -> Path:
    config_path = root / "skills.json"
    config_path.write_text(
        json.dumps({"$schema": "./skills.schema.json", "skills": skills}, indent=2),
        encoding="utf-8",
    )
    return config_path


def run_validator(config_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(config_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_validator_accepts_valid_config(tmp_path: Path) -> None:
    path = write_skill(tmp_path, "docs-helper")
    config_path = write_config(
        tmp_path,
        [
            {
                "name": "docs-helper",
                "path": path,
                "userInvocable": True,
                "triggers": {"keywords": ["library docs", "api reference"]},
            }
        ],
    )

    result = run_validator(config_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skills config OK" in result.stdout


def test_validator_rejects_duplicate_missing_dep_cycle_and_frontmatter(tmp_path: Path) -> None:
    first_path = write_skill(tmp_path, "first-skill")
    second_path = write_skill(tmp_path, "second-skill")
    broken_dir = tmp_path / "skills" / "broken-skill"
    broken_dir.mkdir(parents=True)
    broken_path = broken_dir / "SKILL.md"
    broken_path.write_text("---\nname: wrong-name\n---\n\n# Broken\n", encoding="utf-8")
    write_skill(tmp_path, "long-description", "x" * 1025)
    config_path = write_config(
        tmp_path,
        [
            {"name": "first-skill", "path": first_path, "dependencies": ["second-skill"]},
            {"name": "first-skill", "path": first_path},
            {"name": "second-skill", "path": second_path, "dependencies": ["first-skill"]},
            {"name": "missing-dep", "path": first_path, "dependencies": ["not-real"]},
            {"name": "broken-skill", "path": "skills/broken-skill/SKILL.md"},
            {"name": "long-description", "path": "skills/long-description/SKILL.md"},
            {"name": "missing-path", "path": "skills/missing-path/SKILL.md"},
        ],
    )

    result = run_validator(config_path)

    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "duplicate skill name: first-skill" in output
    assert "missing dependency: missing-dep -> not-real" in output
    assert "dependency cycle:" in output
    assert "frontmatter name mismatch: broken-skill" in output
    assert "missing frontmatter description: broken-skill" in output
    assert "frontmatter description too long: long-description" in output
    assert "missing skill path: missing-path" in output


def test_validator_warns_about_broad_trigger_terms(tmp_path: Path) -> None:
    path = write_skill(tmp_path, "react-pattern")
    config_path = write_config(
        tmp_path,
        [
            {
                "name": "react-pattern",
                "path": path,
                "triggers": {
                    "fileExtensions": ["ts", "js", "tsx", "jsx"],
                    "keywords": ["component", "state", "refactor"],
                },
                "dependencies": ["frontend-scan"],
            },
            {
                "name": "frontend-scan",
                "path": write_skill(tmp_path, "frontend-scan"),
            },
        ],
    )

    result = run_validator(config_path)

    assert result.returncode == 0
    assert "warning: broad trigger keyword in react-pattern: component" in result.stdout
    assert "warning: broad dependency in react-pattern -> frontend-scan" in result.stdout
