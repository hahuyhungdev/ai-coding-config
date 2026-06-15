import os
import sys
import unittest
from importlib.machinery import SourceFileLoader

# Load the agy-status module dynamically due to the hyphen in its name
tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../tools'))
agy_status_path = os.path.join(tools_dir, 'agy-status.py')
agy_status = SourceFileLoader("agy_status", agy_status_path).load_module()

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
        quotas = agy_status.parse_quota_output(output)
        
        # GEMINI MODELS check (Weekly is bottleneck: 71%)
        for m in agy_status.GEMINI_MODELS:
            self.assertEqual(quotas[m]["pct"], 71)
            self.assertEqual(quotas[m]["refresh"], "In 99h 53m")
            self.assertEqual(quotas[m]["weekly_pct"], 71)
            self.assertEqual(quotas[m]["weekly_refresh"], "In 99h 53m")
            self.assertEqual(quotas[m]["five_hour_pct"], 77)
            self.assertEqual(quotas[m]["five_hour_refresh"], "In 4h 53m")
            
        # CLAUDE MODELS check (Weekly is bottleneck: 95%)
        for m in agy_status.CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
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
        quotas = agy_status.parse_quota_output(output)
        
        # GEMINI MODELS check (Five Hour is bottleneck: 0%)
        for m in agy_status.GEMINI_MODELS:
            self.assertEqual(quotas[m]["pct"], 0)
            self.assertEqual(quotas[m]["refresh"], "In 3h 12m")
            self.assertEqual(quotas[m]["weekly_pct"], 100)
            self.assertEqual(quotas[m]["weekly_refresh"], "")
            self.assertEqual(quotas[m]["five_hour_pct"], 0)
            self.assertEqual(quotas[m]["five_hour_refresh"], "In 3h 12m")
            
        # CLAUDE MODELS check (Five Hour is bottleneck: 50%)
        for m in agy_status.CLAUDE_MODELS + ["GPT-OSS 120B (Medium)"]:
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
        quotas = agy_status.parse_quota_output(output)
        
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

if __name__ == "__main__":
    unittest.main()
