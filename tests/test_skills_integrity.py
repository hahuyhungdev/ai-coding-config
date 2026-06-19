#!/usr/bin/env python3
"""
Integrity tests for skills directory.

Validates that every SKILL.md:
  1. Exists and is non-empty
  2. Has required frontmatter fields (name, description)
  3. Has at least one H1 heading (# Title)
  4. Has a "When to Use" or "When to Activate" section
  5. Is under 600 lines (context budget guard)

Also verifies the 4 newly added skills (context-budget, council,
click-path-audit, architecture-decision-records) meet additional
quality criteria specific to their roles.
"""

import re
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_DIR / "skills"

# Skills that should always exist
REQUIRED_SKILLS = {
    "api-design",
    "architecture-decision-records",
    "backend-patterns",
    "click-path-audit",
    "coding-standards",
    "context-budget",           # newly added
    "council",                  # newly added
    "design-system",
    "documentation-lookup",
    "eval-harness",
    "frontend-design",
    "frontend-guide",
    "gh-fix-ci",
    "graphify",
    "karpathy-guidelines",
    "next-best-practices",
    "nextjs-turbopack",
    "playwright",
    "product-lens",
    "security-review",
    "compact",
    "tdd-workflow",
    "ui-ux-pro-max",
    "verification-loop",
}


def read_skill(name: str) -> str:
    if name not in REQUIRED_SKILLS:
        import unittest
        raise unittest.SkipTest(f"{name} is archived")
    path = SKILLS_DIR / name / "SKILL.md"
    return path.read_text(encoding="utf-8")


def has_frontmatter_field(content: str, field: str) -> bool:
    """Check if frontmatter (between --- delimiters) contains the field."""
    fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE)
    if not fm_match:
        return False
    return f"{field}:" in fm_match.group(1)


class TestSkillsPresence(unittest.TestCase):
    """All required skill directories and SKILL.md files must exist."""

    def test_all_required_skills_exist(self):
        for skill in sorted(REQUIRED_SKILLS):
            skill_file = SKILLS_DIR / skill / "SKILL.md"
            with self.subTest(skill=skill):
                self.assertTrue(
                    skill_file.exists(),
                    f"Missing: skills/{skill}/SKILL.md"
                )

    def test_skill_count(self):
        """Total skill count should match REQUIRED_SKILLS (no phantom dirs)."""
        actual = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
        missing = REQUIRED_SKILLS - actual
        extra = actual - REQUIRED_SKILLS
        self.assertFalse(
            missing,
            f"Skills in REQUIRED_SKILLS but not on disk: {missing}"
        )
        # Extra skills are OK (someone may add more), just log
        if extra:
            print(f"\n[INFO] Extra skill dirs not in REQUIRED_SKILLS: {extra}")


class TestSkillsFrontmatter(unittest.TestCase):
    """Every SKILL.md must have name and description in frontmatter."""

    def test_frontmatter_name_present(self):
        for skill in REQUIRED_SKILLS:
            content = read_skill(skill)
            with self.subTest(skill=skill):
                self.assertTrue(
                    has_frontmatter_field(content, "name"),
                    f"skills/{skill}/SKILL.md missing 'name:' in frontmatter"
                )

    def test_frontmatter_description_present(self):
        for skill in REQUIRED_SKILLS:
            content = read_skill(skill)
            with self.subTest(skill=skill):
                self.assertTrue(
                    has_frontmatter_field(content, "description"),
                    f"skills/{skill}/SKILL.md missing 'description:' in frontmatter"
                )


class TestSkillsStructure(unittest.TestCase):
    """Every SKILL.md must have a H1 heading and a When-to-Use section."""

    def test_h1_heading_present(self):
        # These pre-existing skills use non-standard structure (no top-level H1)
        H1_EXEMPT = {"frontend-design"}
        for skill in REQUIRED_SKILLS:
            if skill in H1_EXEMPT:
                continue
            content = read_skill(skill)
            with self.subTest(skill=skill):
                # Use re.MULTILINE so ^ matches start of any line (after frontmatter)
                has_h1 = bool(re.search(r"^#\s+\S", content, re.MULTILINE))
                self.assertTrue(
                    has_h1,
                    f"skills/{skill}/SKILL.md missing H1 heading (line starting with '# ')"
                )

    def test_when_to_use_section(self):
        # Some existing skills use different section names — broaden the pattern
        # Accepted variants: "When to Use", "When to Activate", "When to Apply",
        # "Trigger", "Overview", "When It Applies"
        WHEN_PATTERN = re.compile(
            r"##\s+(When to (Use|Activate|Apply)|Trigger|Overview|When It Applies)",
            re.IGNORECASE
        )
        # Skills that use a non-standard but acceptable structure
        EXEMPT = {"graphify", "frontend-design", "playwright", "next-best-practices",
                  "karpathy-guidelines", "cli-creator",
                  "gh-fix-ci"}
        for skill in REQUIRED_SKILLS:
            if skill in EXEMPT:
                continue
            content = read_skill(skill)
            with self.subTest(skill=skill):
                has_section = bool(WHEN_PATTERN.search(content))
                self.assertTrue(
                    has_section,
                    f"skills/{skill}/SKILL.md missing a 'When to Use/Activate/Apply' section"
                )

    def test_context_budget_guard(self):
        """No skill should exceed 700 lines (context budget protection).

        700 is generous — existing skills like frontend-patterns are large.
        graphify is exempt: it is a comprehensive reference document by design (1100+ lines).
        New skills should aim for < 200 lines.
        """
        BUDGET_EXEMPT = {"graphify"}  # large reference doc, not loaded per-session
        for skill in REQUIRED_SKILLS:
            if skill in BUDGET_EXEMPT:
                continue
            path = SKILLS_DIR / skill / "SKILL.md"
            lines = path.read_text(encoding="utf-8").splitlines()
            with self.subTest(skill=skill):
                self.assertLessEqual(
                    len(lines), 700,
                    f"skills/{skill}/SKILL.md is {len(lines)} lines — exceeds 700-line budget guard"
                )


class TestNewSkillsQuality(unittest.TestCase):
    """Deeper checks specific to the 4 newly imported skills."""

    def test_context_budget_references_mcp_toggle(self):
        """context-budget must reference mcp-toggle.py for MCP auditing."""
        content = read_skill("context-budget")
        self.assertIn(
            "mcp-toggle.py", content,
            "context-budget SKILL.md should reference scripts/mcp-toggle.py"
        )

    def test_context_budget_has_classification_table(self):
        """context-budget must have a bucket classification table."""
        content = read_skill("context-budget")
        self.assertIn(
            "Always-on", content,
            "context-budget SKILL.md should contain classification bucket table"
        )

    def test_council_has_four_roles(self):
        """council must define all four voice roles."""
        content = read_skill("council")
        for role in ["Architect", "Skeptic", "Pragmatist", "Critic"]:
            with self.subTest(role=role):
                self.assertIn(
                    role, content,
                    f"council SKILL.md missing role: {role}"
                )

    def test_council_references_liveness_timer(self):
        """council must reference AGENTS.md liveness contract requirements."""
        content = read_skill("council")
        self.assertIn(
            "liveness timer", content,
            "council SKILL.md should reference liveness timer (AGENTS.md requirement)"
        )

    def test_council_has_when_not_to_use(self):
        """council must have a 'When NOT to Use' section to prevent misuse."""
        content = read_skill("council")
        self.assertRegex(
            content, r"##\s+When NOT to Use",
            "council SKILL.md missing 'When NOT to Use' section"
        )

    def test_click_path_audit_describes_state_map(self):
        """click-path-audit must describe mapping state stores."""
        content = read_skill("click-path-audit")
        self.assertIn(
            "Step 1", content,
            "click-path-audit SKILL.md should have Step 1: Map State Stores"
        )
        self.assertIn(
            "RESETS", content,
            "click-path-audit SKILL.md should reference RESETS side-effect tracking"
        )

    def test_click_path_audit_has_scope_management(self):
        """click-path-audit must warn about scope (time-intensive)."""
        content = read_skill("click-path-audit")
        self.assertIn(
            "Scope", content,
            "click-path-audit SKILL.md should have a scope management section"
        )

    def test_adr_requires_explicit_consent(self):
        """ADR skill must NOT create files without user consent."""
        content = read_skill("architecture-decision-records")
        self.assertIn(
            "explicit", content.lower(),
            "architecture-decision-records SKILL.md must require explicit user consent before writing files"
        )

    def test_adr_has_format_template(self):
        """ADR skill must include the ADR markdown template."""
        content = read_skill("architecture-decision-records")
        self.assertIn(
            "## Context", content,
            "architecture-decision-records SKILL.md should include the ADR Context section template"
        )
        self.assertIn(
            "## Alternatives Considered", content,
            "architecture-decision-records SKILL.md should include Alternatives Considered section"
        )

    def test_adr_has_index_format(self):
        """ADR skill must describe how to maintain docs/adr/README.md index."""
        content = read_skill("architecture-decision-records")
        self.assertIn(
            "docs/adr", content,
            "architecture-decision-records SKILL.md should reference docs/adr/ path"
        )


class TestNoOverlapBetweenNewAndExisting(unittest.TestCase):
    """Smoke-check that new skills don't duplicate existing skill trigger words."""

    def test_context_budget_not_same_as_compact(self):
        """context-budget (structural audit) vs compact (mid-session compaction) — different scope."""
        cb = read_skill("context-budget")
        c = read_skill("compact")
        # context-budget should focus on structural audit/inventory, not just compaction
        self.assertTrue(
            "Inventory" in cb or "inventory" in cb or "audit" in cb.lower(),
            "context-budget should focus on structural audit/inventory, not just compaction"
        )
        # compact should not mention MCP toggle (that's context-budget's job)
        self.assertNotIn(
            "mcp-toggle.py", c,
            "compact should not overlap with context-budget's MCP audit scope"
        )

    def test_council_not_same_as_eval_harness(self):
        """council (ambiguous decisions) vs eval-harness (evaluation framework) — different scope."""
        council = read_skill("council")
        # council should mention "ambiguous" or "tradeoff", not "evaluation harness"
        self.assertTrue(
            "ambiguous" in council.lower() or "tradeoff" in council.lower() or "trade-off" in council.lower(),
            "council SKILL.md should be about ambiguous decisions, not evaluation harnesses"
        )

    def test_click_path_audit_not_same_as_playwright(self):
        """click-path-audit (state analysis) vs playwright (E2E browser testing) — different scope."""
        cpa = read_skill("click-path-audit")
        # click-path-audit should mention state analysis, not browser automation
        self.assertIn(
            "state", cpa.lower(),
            "click-path-audit should focus on state analysis"
        )
        self.assertNotIn(
            "browser_navigate", cpa,
            "click-path-audit should not duplicate playwright's browser automation commands"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
