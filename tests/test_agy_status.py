import os
import sys
import unittest
from importlib.machinery import SourceFileLoader
from unittest.mock import patch

# Load the modular agy package components
tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools/agy'))
sys.path.insert(0, tools_dir)
import parser
import utils

agy_status = SourceFileLoader(
    "agy_status", os.path.join(tools_dir, "agy-status.py")
).load_module()

class TestAgyStatus(unittest.TestCase):
    def test_parse_quota_output_new_weekly_bottleneck(self):
        output = """
  Account: test@gmail.com

GEMINI MODELS
  Models within this group: Gemini Flash, Gemini Pro

  Weekly Limit
    [████████████████████████████████████░░░░░░░░░░░░░░] 71.12%
    71% remaining · Refreshes in 99h 53m

  Five Hour Limit
    [██████████████████████████████████████░░░░░░░░░░░░] 76.53%
    77% remaining · Refreshes in 4h 53m


CLAUDE AND GPT MODELS
  Models within this group: Claude Opus, Claude Sonnet, GPT-OSS

  Weekly Limit
    [███████████████████████████████████████████████░░░] 94.81%
    95% remaining · Refreshes in 104h 56m

  Five Hour Limit
    [██████████████████████████████████████████████████] 100.00%
    Quota available
        """
        quotas = parser.parse_quota_output(output)
        
        # GEMINI MODELS check (Weekly is bottleneck: 71%)
        for m in utils.GEMINI_MODELS:
            self.assertEqual(quotas[m]["pct"], 71)
            self.assertEqual(quotas[m]["refresh"], "In 99h 53m")
            self.assertEqual(quotas[m]["weekly_pct"], 71)
            self.assertEqual(quotas[m]["weekly_refresh"], "In 99h 53m")
            self.assertEqual(quotas[m]["five_hour_pct"], 77)
            self.assertEqual(quotas[m]["five_hour_refresh"], "In 4h 53m")
            
        # CLAUDE MODELS check (Weekly is bottleneck: 95%)
        for m in utils.CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
            self.assertEqual(quotas[m]["pct"], 95)
            self.assertEqual(quotas[m]["refresh"], "In 104h 56m")
            self.assertEqual(quotas[m]["weekly_pct"], 95)
            self.assertEqual(quotas[m]["weekly_refresh"], "In 104h 56m")
            self.assertEqual(quotas[m]["five_hour_pct"], 100)
            self.assertEqual(quotas[m]["five_hour_refresh"], "")

    def test_parse_quota_output_new_five_hour_bottleneck(self):
        output = """
GEMINI MODELS
  Weekly Limit
    [████] 100.00%
    Quota available
  Five Hour Limit
    [░░░░] 0.00%
    0% remaining · Refreshes in 3h 12m
CLAUDE AND GPT MODELS
  Weekly Limit
    [████] 94.81%
    95% remaining · Refreshes in 104h 56m
  Five Hour Limit
    [██░░] 50.00%
    50% remaining · Refreshes in 1h 45m
        """
        quotas = parser.parse_quota_output(output)
        
        # GEMINI MODELS check (Five Hour is bottleneck: 0%)
        for m in utils.GEMINI_MODELS:
            self.assertEqual(quotas[m]["pct"], 0)
            self.assertEqual(quotas[m]["refresh"], "In 3h 12m")
            self.assertEqual(quotas[m]["weekly_pct"], 100)
            self.assertEqual(quotas[m]["weekly_refresh"], "")
            self.assertEqual(quotas[m]["five_hour_pct"], 0)
            self.assertEqual(quotas[m]["five_hour_refresh"], "In 3h 12m")
            
        # CLAUDE MODELS check (Five Hour is bottleneck: 50%)
        for m in utils.CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
            self.assertEqual(quotas[m]["pct"], 50)
            self.assertEqual(quotas[m]["refresh"], "In 1h 45m")
            self.assertEqual(quotas[m]["weekly_pct"], 95)
            self.assertEqual(quotas[m]["weekly_refresh"], "In 104h 56m")
            self.assertEqual(quotas[m]["five_hour_pct"], 50)
            self.assertEqual(quotas[m]["five_hour_refresh"], "In 1h 45m")

    def test_parse_quota_output_old_format_compatibility(self):
        output = """
Model Quotas:
Gemini 3.5 Flash (High)
  [██████████████████████████████████████████████████] 100%
  Quota available
Claude Opus 4.6 (Thinking)
  [██████████████████████████████████████░░░░░░░░░░░░] 76%
  76% remaining · Refreshes in 2h 15m
        """
        quotas = parser.parse_quota_output(output)
        
        # High Gemini model check
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["pct"], 100)
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["refresh"], "")
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["weekly_pct"], 100)
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["weekly_refresh"], "")
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["five_hour_pct"], 100)
        self.assertEqual(quotas["Gemini 3.5 Flash (High)"]["five_hour_refresh"], "")
        
        # High Claude model check
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["pct"], 76)
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["refresh"], "In 2h 15m")
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["weekly_pct"], 76)
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["weekly_refresh"], "In 2h 15m")
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["five_hour_pct"], 76)
        self.assertEqual(quotas["Claude Opus 4.6 (Thinking)"]["five_hour_refresh"], "In 2h 15m")

    def test_status_defaults_to_live_refresh(self):
        with patch.object(agy_status, "get_account_status") as get_status, \
             patch.object(agy_status, "account_list") as account_list:
            agy_status.run_status(refresh=False, json_output=False)

        get_status.assert_called_once_with()
        account_list.assert_not_called()

    def test_sort_rows_by_effective_remaining_quota_descending(self):
        rows = [
            {"index": 1, "quota": "5H:50%/W:100%"},
            {"index": 2, "quota": "100%"},
            {"index": 3, "quota": "🔴 0% (Blocked)"},
            {"index": 4, "quota": "5H:80%/W:75%"},
        ]

        sorted_rows = agy_status.sort_rows_by_remaining_quota(rows)

        self.assertEqual([row["index"] for row in sorted_rows], [2, 4, 1, 3])

    def test_sort_rows_by_effective_remaining_quota_and_reset_seconds(self):
        rows = [
            {"index": 1, "quota": "5H:70%/W:100%", "reset_seconds": 356400}, # 70%, resets in 99h
            {"index": 2, "quota": "5H:70%/W:100%", "reset_seconds": 7200},   # 70%, resets in 2h
            {"index": 3, "quota": "100%"},                                   # 100%
            {"index": 4, "quota": "🔴 0% (Blocked)", "reset_seconds": 86400}, # 0%, resets in 24h
            {"index": 5, "quota": "🔴 0% (Blocked)", "reset_seconds": 7200},  # 0%, resets in 2h
        ]

        sorted_rows = agy_status.sort_rows_by_remaining_quota(rows)

        # Expected order:
        # Index 3 (100%)
        # Index 2 (70%, 2h reset)
        # Index 1 (70%, 99h reset)
        # Index 5 (0%, 2h reset)
        # Index 4 (0%, 24h reset)
        self.assertEqual([row["index"] for row in sorted_rows], [3, 2, 1, 5, 4])

if __name__ == "__main__":
    unittest.main()
