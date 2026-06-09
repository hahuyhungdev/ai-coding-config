import json
import unittest
from pathlib import Path

try:
    import tomllib
except ImportError:
    tomllib = None


REPO_DIR = Path(__file__).resolve().parent.parent


class TestAiCodingConfig(unittest.TestCase):
    def test_configuration_syntax(self):
        with (REPO_DIR / "claude" / "settings.json").open(encoding="utf-8") as handle:
            self.assertIn("permissions", json.load(handle))

        with (REPO_DIR / "gemini" / "settings.json").open(encoding="utf-8") as handle:
            self.assertIn("trustedWorkspaces", json.load(handle))

        if tomllib:
            with (REPO_DIR / "codex" / "config.toml").open("rb") as handle:
                self.assertIn("approval_policy", tomllib.load(handle))


if __name__ == "__main__":
    unittest.main()
