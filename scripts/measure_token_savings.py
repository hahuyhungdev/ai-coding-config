import sys
import os
import re

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Define original instructions
ORIGINAL_GUIDANCE = (
    "⚠️ GRAPHIFY WORKFLOW RULES (MANDATORY — READ BEFORE ANY CODEBASE EXPLORATION):\n\n"
    "**CRITICAL: For ANY question about codebase structure, architecture, or file relationships, your VERY FIRST tool call MUST be `rtk graphify query \"<question>\"`. Do NOT use `list_dir`, `grep_search`, `find`, `cat`, or `view_file` as your first exploration step. Graphify-first is non-negotiable.**\n\n"
    "Commands:\n"
    "- Architecture questions → `rtk graphify query \"question\"`\n"
    "- Code relationships → `rtk graphify path \"A\" \"B\"`\n"
    "- Deep-dive concepts → `rtk graphify explain \"concept\"`\n"
    "- Impact analysis / reverse dependencies → `rtk graphify affected \"SymbolName\"`"
)

ORIGINAL_INSTRUCTIONS = f"""## graphify

{ORIGINAL_GUIDANCE}

Rules:
- For codebase exploration, use **Graphify-only**. Do NOT use view_file, list_dir, cat, grep, sed, awk, or inline scripts to explore.
- Use at most **20 Graphify calls** total per question. After 20 calls, hard stop and synthesize from available context.
- **Focus queries on specific symbols** — prefer `graphify query \"what does X do\"` over `graphify query \"explain the codebase\"`.
- **Synthesize from Graphify context only.** Answer based on what Graphify returns. Do not supplement with direct file reads for exploration.
- **If a tool call is blocked, do not retry.** Proceed and answer using the available context.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only when scoped queries are insufficient or the user requests a broad report.

Post-Discovery Reads (exceptions):
- After Graphify discovery, targeted raw reads ARE allowed for: **editing**, **debugging**, and **config review** of specific files already identified by Graphify.
- You MUST have run at least one Graphify query before reading source files directly.
- When reading after discovery, state your justification (e.g., \"Reading for editing\" or \"Verifying config structure\").
- After modifying code, run `graphify update .`.

Blocked Tool Recovery:
- If a hook blocks a direct read/search or inline script, do not retry the same blocked call or attempt an equivalent bypass.
- Do not create one-off scratch scripts to inspect facts that a project diagnostic already covers.
- For conversation log debugging in this repo, use `rtk python3 scripts/inspect_conversation.py <conversation_id> --step-index <n> --keyword \"<text>\"`; add `--compare-logs` when comparing compact vs full transcripts.
- When debugging truncation, measure full content length and keyword presence; do not use substring-only previews as evidence.
"""

def main():
    try:
        from installer_graphify import GRAPHIFY_INSTRUCTIONS as new_instructions
    except ImportError as e:
        print(f"Error importing installer_graphify: {e}", file=sys.stderr)
        sys.exit(1)

    print("=== Original Instructions ===")
    print(ORIGINAL_INSTRUCTIONS)
    print("=== New Instructions ===")
    print(new_instructions)
    print("==========================")

    # Calculate metrics
    orig_chars = len(ORIGINAL_INSTRUCTIONS)
    new_chars = len(new_instructions)
    
    orig_words = len(ORIGINAL_INSTRUCTIONS.split())
    new_words = len(new_instructions.split())

    # Try tiktoken
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        orig_tokens = len(encoding.encode(ORIGINAL_INSTRUCTIONS))
        new_tokens = len(encoding.encode(new_instructions))
        token_method = "tiktoken (cl100k_base)"
    except ImportError:
        # Fallback to rough heuristic: 1 token ~ 4 chars / 0.75 words
        # cl100k_base is close to character / 3.8
        orig_tokens = round(orig_chars / 3.8)
        new_tokens = round(new_chars / 3.8)
        token_method = "heuristic approximation (char count / 3.8)"

    char_savings = (orig_chars - new_chars) / orig_chars * 100
    word_savings = (orig_words - new_words) / orig_words * 100
    token_savings = (orig_tokens - new_tokens) / orig_tokens * 100

    print(f"Original Char Count: {orig_chars}")
    print(f"New Char Count:      {new_chars}")
    print(f"Char Savings:        {char_savings:.2f}%")
    print()
    print(f"Original Word Count: {orig_words}")
    print(f"New Word Count:      {new_words}")
    print(f"Word Savings:        {word_savings:.2f}%")
    print()
    print(f"Tokenization Method: {token_method}")
    print(f"Original Tokens:     {orig_tokens}")
    print(f"New Tokens:          {new_tokens}")
    print(f"Token Savings:       {token_savings:.2f}%")

    if token_savings < 15.0:
        print("Error: Token savings are less than 15%!", file=sys.stderr)
        sys.exit(1)
    else:
        print("Success: Token savings exceed 15%!")

if __name__ == "__main__":
    main()
