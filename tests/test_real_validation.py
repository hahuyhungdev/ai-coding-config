#!/usr/bin/env python3
"""Real validation tests — test actual logic, not mocks."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path

# Load switch module
tools_dir = str(Path(__file__).resolve().parent.parent / "tools" / "agy")
sys.path.insert(0, tools_dir)
import switch
import utils

# Load agy-status module (hyphenated filename)
spec = importlib.util.spec_from_file_location("agy_status", os.path.join(tools_dir, "agy-status.py"))
agy_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agy_status)


class TestRealFallbackLogic(unittest.TestCase):
    """Test choose_same_account_fallback with real model constants."""

    def test_gemini_blocked_does_not_suggest_claude(self):
        acc = {"model_quotas": {utils.CLAUDE_FALLBACK_MODEL: {"pct": 100}}}
        result = switch.choose_same_account_fallback(acc, blocked_model="gemini")
        self.assertEqual(result, "")

    def test_claude_blocked_never_suggests_gemini(self):
        acc = {"model_quotas": {utils.GEMINI_FALLBACK_MODEL: {"pct": 100}}}
        result = switch.choose_same_account_fallback(acc, blocked_model="claude")
        self.assertEqual(result, "")

    def test_no_block_prefers_gemini(self):
        acc = {"model_quotas": {
            utils.GEMINI_FALLBACK_MODEL: {"pct": 100},
            utils.CLAUDE_FALLBACK_MODEL: {"pct": 100}
        }}
        result = switch.choose_same_account_fallback(acc)
        self.assertEqual(result, utils.GEMINI_FALLBACK_MODEL)

    def test_gemini_exhausted_does_not_suggest_claude(self):
        acc = {"model_quotas": {
            utils.GEMINI_FALLBACK_MODEL: {"pct": 0},
            utils.CLAUDE_FALLBACK_MODEL: {"pct": 80}
        }}
        result = switch.choose_same_account_fallback(acc)
        self.assertEqual(result, "")

    def test_gemini_blocked_no_claude_quota_returns_empty(self):
        acc = {"model_quotas": {utils.CLAUDE_FALLBACK_MODEL: {"pct": 0}}}
        result = switch.choose_same_account_fallback(acc, blocked_model="gemini")
        self.assertEqual(result, "")

    def test_no_model_quotas_returns_empty(self):
        result = switch.choose_same_account_fallback({})
        self.assertEqual(result, "")


class TestRealTranslateLegacyArgs(unittest.TestCase):
    """Test translate_legacy_args with real CLI patterns."""

    def test_account_list(self):
        self.assertEqual(agy_status.translate_legacy_args(["account", "list"]), ["list"])

    def test_account_current(self):
        self.assertEqual(agy_status.translate_legacy_args(["account", "current"]), ["current"])

    def test_account_use_with_target(self):
        self.assertEqual(agy_status.translate_legacy_args(["account", "use", "2"]), ["use", "2"])

    def test_account_rename_with_args(self):
        self.assertEqual(agy_status.translate_legacy_args(["account", "rename", "2", "work"]), ["rename", "2", "work"])

    def test_account_remove_with_yes(self):
        self.assertEqual(agy_status.translate_legacy_args(["account", "remove", "2", "--yes"]), ["remove", "2", "--yes"])

    def test_json_account_list(self):
        self.assertEqual(agy_status.translate_legacy_args(["--json", "account", "list"]), ["--json", "list"])

    def test_json_account_add_with_label(self):
        self.assertEqual(
            agy_status.translate_legacy_args(["--json", "account", "add", "--label", "personal"]),
            ["--json", "add", "--label", "personal"]
        )

    def test_help_status(self):
        self.assertEqual(agy_status.translate_legacy_args(["help", "status"]), ["status", "--help"])

    def test_ls_alias(self):
        self.assertEqual(agy_status.translate_legacy_args(["ls"]), ["list"])

    def test_accounts_alias(self):
        self.assertEqual(agy_status.translate_legacy_args(["accounts"]), ["list"])

    def test_compact_alias(self):
        self.assertEqual(agy_status.translate_legacy_args(["compact"]), ["clean"])

    def test_typo_stays_for_argparse(self):
        self.assertEqual(agy_status.translate_legacy_args(["acount", "list"]), ["acount", "list"])

    def test_passthrough(self):
        self.assertEqual(agy_status.translate_legacy_args(["status"]), ["status"])

    def test_empty_args(self):
        self.assertEqual(agy_status.translate_legacy_args([]), [])


class TestRealArgparseErrorHandling(unittest.TestCase):
    """Test that argparse errors produce helpful suggestions."""

    def test_unknown_subcommand_suggests(self):
        """Calling with a typo should suggest the closest match."""
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        try:
            with redirect_stderr(stderr_capture):
                agy_status.main(["account", "lits"])
        except SystemExit:
            pass
        stderr = stderr_capture.getvalue()
        self.assertIn("Unknown command: lits", stderr)
        self.assertIn("Did you mean:", stderr)
        self.assertIn("agy account list", stderr)

    def test_unknown_top_level_suggests(self):
        """Calling with a top-level typo should suggest closest match."""
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        try:
            with redirect_stderr(stderr_capture):
                agy_status.main(["s"])
        except SystemExit:
            pass
        stderr = stderr_capture.getvalue()
        self.assertIn("Unknown command: s", stderr)
        self.assertIn("Did you mean:", stderr)

    def test_json_account_typo_suggests(self):
        """--json account lits should suggest list."""
        import io
        from contextlib import redirect_stderr
        stderr_capture = io.StringIO()
        try:
            with redirect_stderr(stderr_capture):
                agy_status.main(["--json", "account", "lits"])
        except SystemExit:
            pass
        stderr = stderr_capture.getvalue()
        self.assertIn("lits", stderr)
        self.assertIn("list", stderr)


if __name__ == "__main__":
    unittest.main()
