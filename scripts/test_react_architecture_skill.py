#!/usr/bin/env python3
"""Smoke tests for the react-architecture skill resources."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "react-architecture"
FRONTEND_DIR = ROOT / "frontend"
GENERATE_FEATURE = SKILL_DIR / "scripts" / "generate-feature.py"
GENERATE_COMPONENT = SKILL_DIR / "scripts" / "generate-component.py"
CHECK_ARCHITECTURE = SKILL_DIR / "scripts" / "check-architecture.mjs"


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def create_react_fixture(temp_root: Path) -> Path:
    fixture = temp_root / "react-app"
    (fixture / "src").mkdir(parents=True)
    shutil.copy(FRONTEND_DIR / "package.json", fixture / "package.json")

    source_node_modules = FRONTEND_DIR / "node_modules"
    if source_node_modules.exists():
        (fixture / "node_modules").symlink_to(source_node_modules, target_is_directory=True)

    return fixture


class ReactArchitectureSkillTests(unittest.TestCase):
    def test_generate_feature_output_passes_architecture_checker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="react-arch-skill-") as temp_dir:
            fixture = create_react_fixture(Path(temp_dir))

            generate_result = run([sys.executable, str(GENERATE_FEATURE), "user-profile"], fixture)
            self.assertEqual(
                generate_result.returncode,
                0,
                generate_result.stdout + generate_result.stderr,
            )

            self.assertTrue((fixture / "src" / "features" / "user-profile" / "index.tsx").exists())
            self.assertTrue(
                (
                    fixture
                    / "src"
                    / "features"
                    / "user-profile"
                    / "components"
                    / "UserProfileView"
                    / "index.tsx"
                ).exists()
            )

            check_result = run(["node", str(CHECK_ARCHITECTURE)], fixture)
            self.assertEqual(
                check_result.returncode,
                0,
                check_result.stdout + check_result.stderr,
            )

            check_from_repo_root = run(["node", str(CHECK_ARCHITECTURE), str(fixture)], ROOT)
            self.assertEqual(
                check_from_repo_root.returncode,
                0,
                check_from_repo_root.stdout + check_from_repo_root.stderr,
            )

    def test_generate_component_output_passes_architecture_checker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="react-arch-skill-") as temp_dir:
            fixture = create_react_fixture(Path(temp_dir))

            generate_result = run(
                [sys.executable, str(GENERATE_COMPONENT), "status-badge", "src/components", "--scss"],
                fixture,
            )
            self.assertEqual(
                generate_result.returncode,
                0,
                generate_result.stdout + generate_result.stderr,
            )
            self.assertTrue((fixture / "src" / "components" / "StatusBadge" / "index.tsx").exists())

            check_result = run(["node", str(CHECK_ARCHITECTURE)], fixture)
            self.assertEqual(
                check_result.returncode,
                0,
                check_result.stdout + check_result.stderr,
            )

    def test_checker_rejects_component_files_named_after_the_component(self) -> None:
        with tempfile.TemporaryDirectory(prefix="react-arch-skill-") as temp_dir:
            fixture = create_react_fixture(Path(temp_dir))
            feature_component = (
                fixture
                / "src"
                / "features"
                / "dashboard"
                / "components"
                / "DashboardView"
                / "DashboardView.tsx"
            )
            shared_component = fixture / "src" / "components" / "StatusBadge" / "StatusBadge.tsx"
            feature_component.parent.mkdir(parents=True)
            shared_component.parent.mkdir(parents=True)
            feature_component.write_text("export function DashboardView() { return null; }\n", encoding="utf-8")
            shared_component.write_text("export function StatusBadge() { return null; }\n", encoding="utf-8")

            check_result = run(["node", str(CHECK_ARCHITECTURE)], fixture)
            self.assertNotEqual(check_result.returncode, 0)
            self.assertIn("components/DashboardView/index.tsx", check_result.stderr)
            self.assertIn("components/StatusBadge/index.tsx", check_result.stderr)

    def test_checker_allows_feature_internal_component_composition(self) -> None:
        with tempfile.TemporaryDirectory(prefix="react-arch-skill-") as temp_dir:
            fixture = create_react_fixture(Path(temp_dir))
            parent = fixture / "src" / "features" / "dashboard" / "components" / "DashboardView" / "index.tsx"
            child = fixture / "src" / "features" / "dashboard" / "components" / "MetricRow" / "index.tsx"
            parent.parent.mkdir(parents=True)
            child.parent.mkdir(parents=True)
            parent.write_text(
                "import { MetricRow } from '../MetricRow';\n"
                "export function DashboardView() { return <MetricRow />; }\n",
                encoding="utf-8",
            )
            child.write_text("export function MetricRow() { return null; }\n", encoding="utf-8")

            check_result = run(["node", str(CHECK_ARCHITECTURE)], fixture)
            self.assertEqual(
                check_result.returncode,
                0,
                check_result.stdout + check_result.stderr,
            )

    def test_checker_rejects_feature_index_import_export_barrel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="react-arch-skill-") as temp_dir:
            fixture = create_react_fixture(Path(temp_dir))
            feature_index = fixture / "src" / "features" / "dashboard" / "index.tsx"
            private_component = (
                fixture
                / "src"
                / "features"
                / "dashboard"
                / "components"
                / "DashboardView"
                / "index.tsx"
            )
            feature_index.parent.mkdir(parents=True)
            private_component.parent.mkdir(parents=True)
            private_component.write_text(
                "export function DashboardView() { return null; }\n",
                encoding="utf-8",
            )
            feature_index.write_text(
                "import { DashboardView } from './components/DashboardView';\n"
                "export { DashboardView };\n",
                encoding="utf-8",
            )

            check_result = run(["node", str(CHECK_ARCHITECTURE)], fixture)
            self.assertNotEqual(check_result.returncode, 0)
            self.assertIn(
                'feature indexes must define public components, not export imported component "DashboardView"',
                check_result.stderr,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
