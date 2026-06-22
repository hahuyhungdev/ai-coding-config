import sys
import json
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None


REPO_DIR = Path(__file__).resolve().parent.parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))


class TestAiCodingConfig(unittest.TestCase):
    def test_configuration_syntax(self):
        with (REPO_DIR / "claude" / "settings.json").open(encoding="utf-8") as handle:
            self.assertIn("permissions", json.load(handle))

        with (REPO_DIR / "gemini" / "settings.json").open(encoding="utf-8") as handle:
            self.assertIn("trustedWorkspaces", json.load(handle))

        if tomllib:
            with (REPO_DIR / "codex" / "config.toml").open("rb") as handle:
                self.assertIn("approval_policy", tomllib.load(handle))

    def test_base_instructions_include_anti_loop_debug_rules(self):
        content = (REPO_DIR / "templates" / "base_instructions.md").read_text(encoding="utf-8")

        self.assertIn("Anti-Loop Debugging", content)
        self.assertIn("do not retry the same blocked tool call", content)
        self.assertIn("diagnostic scripts", content)
        self.assertIn("scratch scripts", content)

    def test_project_graphify_block_includes_blocked_tool_recovery(self):
        import installer_graphify

        self.assertIn("Blocked Tool Recovery", installer_graphify.GRAPHIFY_INSTRUCTIONS)
        self.assertIn("Do not create one-off scratch scripts", installer_graphify.GRAPHIFY_INSTRUCTIONS)
        self.assertIn("scripts/inspect_conversation.py", installer_graphify.GRAPHIFY_INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
