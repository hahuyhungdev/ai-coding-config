#!/usr/bin/env bash
# E2E Real CLI Hook Test
# Tests: agy (Gemini), claude, codex
# Verifies: hooks block exploration reads → AI uses graphify query instead
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$PROJECT_DIR/scratch/e2e_results"
rm -rf "$RESULTS_DIR" && mkdir -p "$RESULTS_DIR"

PROMPT="Explain the main flow and structure of this project. What are the key entry points and how do they connect? Ask me 3-5 follow-up questions about the architecture."

echo "============================================================"
echo "🧪 E2E Real CLI Hook Test"
echo "============================================================"
echo "Project: $PROJECT_DIR"
echo "Graph:   $(ls -lh $PROJECT_DIR/graphify-out/graph.json 2>/dev/null | awk '{print $5}')"
echo "Prompt:  $PROMPT"
echo ""

# ── Test 1: Gemini (agy) ─────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔵 Test 1: Gemini (agy)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Clear debug file
> "$PROJECT_DIR/hook-debug-claude.json" 2>/dev/null || true

timeout 300 env GRAPHIFY_DEBUG=1 agy -p "$PROMPT" < /dev/null > "$RESULTS_DIR/agy_stdout.txt" 2> "$RESULTS_DIR/agy_stderr.txt" || true

echo "  Exit: $?"
echo "  Hook debug log:"
if [ -f "$PROJECT_DIR/hook-debug-claude.json" ]; then
  cat "$PROJECT_DIR/hook-debug-claude.json" | head -30
fi
echo ""
echo "  STDOUT (first 50 lines):"
head -50 "$RESULTS_DIR/agy_stdout.txt"
echo ""
echo "  STDERR (hook debug lines):"
grep -i "GRAPHIFY_HOOK_DEBUG\|graphify\|BLOCKED\|deny" "$RESULTS_DIR/agy_stderr.txt" 2>/dev/null | head -20 || echo "  (none)"
echo ""

# ── Test 2: Claude ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🟣 Test 2: Claude"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

> "$PROJECT_DIR/hook-debug-claude.json" 2>/dev/null || true

timeout 300 env GRAPHIFY_DEBUG=1 claude -p "$PROMPT" 2> "$RESULTS_DIR/claude_stderr.txt" > "$RESULTS_DIR/claude_stdout.txt" || true

echo "  Exit: $?"
echo "  STDOUT (first 50 lines):"
head -50 "$RESULTS_DIR/claude_stdout.txt"
echo ""
echo "  STDERR (hook debug lines):"
grep -i "GRAPHIFY_HOOK_DEBUG\|graphify\|BLOCKED\|deny" "$RESULTS_DIR/claude_stderr.txt" 2>/dev/null | head -20 || echo "  (none)"
echo ""

# ── Test 3: Codex ─────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🟢 Test 3: Codex"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

> "$PROJECT_DIR/hook-debug-claude.json" 2>/dev/null || true

timeout 300 env GRAPHIFY_DEBUG=1 codex exec "$PROMPT" 2> "$RESULTS_DIR/codex_stderr.txt" > "$RESULTS_DIR/codex_stdout.txt" || true

echo "  Exit: $?"
echo "  STDOUT (first 50 lines):"
head -50 "$RESULTS_DIR/codex_stdout.txt"
echo ""
echo "  STDERR (hook debug lines):"
grep -i "GRAPHIFY_HOOK_DEBUG\|graphify\|BLOCKED\|deny" "$RESULTS_DIR/codex_stderr.txt" 2>/dev/null | head -20 || echo "  (none)"
echo ""

# ── Summary ─────────────────────────────────────────────────────
echo "============================================================"
echo "📊 Summary"
echo "============================================================"
for cli in agy claude codex; do
  echo ""
  echo "── $cli ──"
  echo "  graphify calls: $(grep -ci 'graphify' "$RESULTS_DIR/${cli}_stdout.txt" 2>/dev/null || echo 0)"
  echo "  blocked events: $(grep -ci 'BLOCKED\|deny' "$RESULTS_DIR/${cli}_stderr.txt" 2>/dev/null || echo 0)"
  echo "  output size:    $(wc -c < "$RESULTS_DIR/${cli}_stdout.txt" 2>/dev/null || echo 0) bytes"
done
echo ""
echo "Full results in: $RESULTS_DIR/"
