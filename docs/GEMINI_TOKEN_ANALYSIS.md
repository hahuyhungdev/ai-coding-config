# 🧠 Deep Analysis: Gemini Token, Session, & Context Window Strategy

This report analyzes how local AI agents (e.g., Antigravity, Claude Code, Codex) manage the Gemini API payload, how the context window grows, and the strategies used to control token limits and minimize API costs.

---

## 1. 📦 Detailed API Payload Structure

Whenever the local CLI client calls the Gemini API (`generateContent` endpoint), the JSON body is structured as follows:

```yaml
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent
Headers:
  Content-Type: application/json
  x-goog-api-key: sk-gemini-*******       # Layer 1 Authn Gate
Body:
  systemInstruction:
    parts:
      - text: |
          You are Antigravity, designed by Google DeepMind...
          Active Workspaces: /home/huyhung/projects/personals/...
          [Rules]: Always run TDD, prefix commands with rtk, etc.
          [Skills]: Listing local packages...
  tools:
    - functionDeclarations:
        - name: run_command
          description: Execute bash command
        - name: view_file
          description: View file content
        # ... Includes up to 30+ custom MCP tool schemas (e.g., context7, memory)
  contents:
    # ─── TURN 1 ───
    - role: user
      parts:
        - text: "Đọc file server.py"
    - role: model
      parts:
        - text: "Tôi sẽ đọc tệp tin này..."
        - functionCall:
            name: view_file
            args: { AbsolutePath: "/path/to/server.py", StartLine: 1, LineCount: 100 }
    - role: user
      parts:
        - functionResponse:
            name: view_file
            response: { output: "def get_all_mcp_servers()..." }
    # ─── TURN 2 ───
    - role: user
      parts:
        - text: "Giải thích hàm đó"
```

### Key Elements that Consume the Context Window:
1.  **System Instruction (Static Overhead):** ~5k - 25k tokens depending on rules (`AGENTS.md`, `CLAUDE.md`, list of active skills).
2.  **Tool Declarations (Static Overhead):** ~1.5k tokens for schemas of all registered MCP functions.
3.  **Message History (`contents`) (Dynamic Growth):** Grows with *every* user prompt, model thinking, tool invocation (`functionCall`), and tool execution result (`functionResponse`).

---

## 2. 📉 Context Window Growth & Compaction Strategy

As a session continues, the `contents` history grows linearly. If you view a 20KB code file, that file's content remains in the history and is re-sent to the API with *every subsequent request*.

### The Compaction Mechanism
To prevent context overflow and reduce latency/costs, the CLI implements an **automatic context compaction strategy**:

1.  **Threshold Check:** When the total token size of `contents` exceeds a predefined limit (e.g., 60k or 100k tokens), compaction is triggered.
2.  **Summarization:** The agent sends the history to the model with a instruction to synthesize a **Compaction Summary** containing:
    *   What has been accomplished so far.
    *   The current state of the codebase.
    *   Open questions and next steps.
3.  **Truncation:** The CLI discards the raw middle turns (including large file outputs and shell terminal logs).
4.  **Resumption:** It injects a system-style user message to start the new compacted window:
    ```
    [COMPACTION SUMMARY] Resuming from compaction... [conversation-id]
    ```

---

## 3. 💰 Cost & Status Analysis: Flash vs Pro

The token records show a stark contrast between model tiers for long developer sessions:

### Rates (Gemini 3.5 API pricing per 1M tokens)
| Model Tier | Input Rate / 1M | Output Rate / 1M |
|---|---|---|
| **Gemini 3.5 Flash** | $0.075 | $0.30 |
| **Gemini 3.5 Pro** | $1.25 | $5.00 |

### Session Comparison (Real Stats from affc03bb)
For a session with **132 steps** (8 turns):
*   **Total Input Tokens:** `246,385`
*   **Total Output Tokens:** `5,175`
*   **Estimated Gemini 3.5 Pro Cost:** **$0.3339**
*   **Estimated Gemini 3.5 Flash Cost:** **$0.0200**

For a long session with **1,374 steps** (47 turns):
*   **Total Input Tokens:** `1,415,395`
*   **Total Output Tokens:** `72,721`
*   **Estimated Gemini 3.5 Flash Cost:** **$0.127971**

> [!TIP]
> Running complex multi-step tasks on **Gemini 3.5 Flash** is highly cost-effective, saving over **94%** compared to Pro while handling hundreds of tool-execution steps comfortably.

---

## 4. 🛡️ The Graphify Token Savings Strategy

To prevent the context window from bloating in the first place, the repository uses **Graphify**:

```
[Naive AI search] ───> run recursive grep ───> dump files into context (40,000+ tokens)
[Graphify AI search] ─> query local graph.json ─> return precise subgraphs (~300 tokens)
```

Instead of sending full file contents or large directories to search for dependencies, the agent uses the local semantic knowledge graph (`graphify-out/graph.json`) to find exact cross-file relationships, resulting in a **99.8% token reduction** on architectural search queries.
