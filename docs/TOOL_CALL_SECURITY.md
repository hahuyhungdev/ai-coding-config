# Tool Calling Security Model
## A Deep Dive into AI CLI Agent Architecture (Claude Code, Codex CLI, Aider, etc.)

This document outlines the security architecture and threat model of local AI Coding Agent CLIs. These agents communicate with cloud-hosted Large Language Models (LLMs) but execute code and terminal commands locally on your host operating system.

---

### 🔄 7-Step Tool Calling Flow of AI CLI (Developer -> Cloud -> AI CLI -> Response)

1. **Developer Prompt**: You type *"Read file App.tsx for me"* in the terminal.
2. **Sent to Cloud (Layer 1 - API Key)**: The **AI CLI** sends the request to the Cloud AI along with the **API Key** (credentials) to verify identity, billing limits, and model access permissions.
3. **AI Issues Instruction (Layer 2 - `tool_use_id`)**: The model recognizes it needs to use a tool to read the file. It generates an instruction: *"Please read App.tsx"*, assigns it an envelope identifier: **`tool_use_id: 123`**, and sends it back to your machine.
4. **Safety Routing (Layer 4 - Consent Gate)**: The **AI CLI** client receives the instruction. If it is a dangerous command (like modifying files or running scripts), it **pauses** and prompts you for confirmation (`y/N`). Reading a file is low-risk, so it executes automatically.
5. **Execution (Layer 3 & Layer 5 - OS & Sandbox)**: The **AI CLI** uses your active **user privileges on the host system (OS Permissions)** to execute the action. If configured to run inside a **Docker container (Sandbox)**, the execution is isolated to prevent accidental host system damage.
6. **Package Result (Layer 2 - ID Matching)**: Once the action is complete, the **AI CLI** packages the output, stamps it with the corresponding **`tool_use_id: 123`**, and sends it back to the Cloud AI.
7. **AI Final Response**: Cloud AI receives the payload, matches the ID `123` with the pending request, reads the content, and generates the final response, displaying it to you via **AI CLI**.

---

### ⚠️ Physical Vulnerability on Your Machine (Layer 6 - Local Secrets)
All API Keys, configurations, and chat logs are stored in **plaintext** inside a local config directory (e.g., `~/.claude/` or `~/.codex/`) on your machine. If your system is compromised by local malware (like a malicious package in another project), attackers can read this directory to steal your API credentials and code history without needing remote network exploits.

---

### Simple Flow Diagram (Vertical Flow)

```mermaid
graph TD
    Dev["1. Developer enters prompt"] -->|HTTPS Request + API Key| Cloud["2. Cloud AI (Analyzes Prompt)"]
    Cloud -->|3. Tool Request + tool_use_id| Client["4. AI CLI Client (Local OS)"]
    Client -->|5. Consent Gate / OS Execution| Host["6. File Read / Command Run"]
    Host -->|7. Tool Output| Client
    Client -->|8. HTTPS Response + tool_use_id| Cloud
    Cloud -->|9. Final Response| Dev
```

---

## The 6-Layer Security Model

The security posture of an AI CLI agent is composed of six distinct layers, separating cloud-based authorization from local execution boundaries.

---

### Layer 1: API Credentials (Authentication & Authorization)
AI CLIs do not just "compare string keys" locally. The credentials (API Key or OAuth Bearer Token) are sent in the HTTPS headers of every request to the cloud provider (e.g., Anthropic, OpenAI, Google).

* **Purpose**: Identity and account validation.
* **Key functions determined on the Cloud Provider side**:
  * **Authentication**: Verifying who is making the request.
  * **Authorization**: Determining which models the client is permitted to call.
  * **Rate Limits**: Applying rate-limiting policies corresponding to the account tier.
  * **Billing & Quota**: Computing cost per token and deducting from the account balance.

---

### Layer 2: `tool_use_id` (Correlation & State Integrity)
A common misconception in Tool Calling literature is that `tool_use_id` acts as an access token or an anti-forgery credential. In reality, it is a **Correlation Identifier** (or Request-Response Matcher).

```text
[Cloud Model]  --- tool_use (id: "toolu_123", name: "read_file") --->  [Local CLI Client]
                                                                               |
                                                                        (Reads File)
                                                                               |
[Cloud Model]  <-- tool_result (tool_use_id: "toolu_123", content) --  [Local CLI Client]
```

* **Purpose**: Conversation State Integrity.
* **Mechanisms**:
  * The cloud model generates a unique `tool_use_id` (e.g., `toolu_123`) when requesting a tool call.
  * The local CLI client must return the result mapped to that exact `tool_use_id` in the next message.
  * If the IDs do not match (e.g., Tool Use A but Tool Result B), the API server rejects the request because it cannot construct a valid sequential conversation history.
  * **Security Value**: While not an authentication credential, it prevents out-of-context payload injection. For example, if an attacker attempts to inject a malicious string (like `Database password = admin`) into the pipeline, the server will ignore or reject it unless it is wrapped in a valid, active `tool_use_id` currently expected by the model.

---

### Layer 3: OS Permissions & Privilege Inheritance
From the host operating system's perspective, the AI agent is not "special". It is simply a local process running under the user's active session.

* **Purpose**: Local boundary execution.
* **Mechanisms**:
  * The CLI process inherits the user's active **UID (User ID)** on Linux/macOS or **User Token** on Windows.
  * The agent possesses the exact same read, write, and execute permissions as the developer running the command.
  * If the developer has write access to the project source, read access to `~/.ssh/id_rsa`, or permission to execute `rm -rf /`, **so does the AI agent**.
  * **Risk**: If the agent hallucinates or is prompted to run destructive commands, it can modify or delete files directly in the host OS.

---

### Layer 4: Consent Gates (Human-in-the-Loop)
Because local process execution inherits all user privileges, CLI clients implement interactive gates for dangerous or write operations.

* **Purpose**: Human authorization of high-risk actions.
* **Mechanisms**:
  * Low-risk tools (e.g., `view_file` to read read-only code) run automatically to maintain a fast developer flow.
  * High-risk tools (e.g., `run_command` to execute terminal scripts, `replace_file_content` to make modifications, or git actions) trigger a terminal prompt asking the user for confirmation (`[y/N]`).
  * **Caveat**: Consent Gates can be bypassed entirely via startup flags (e.g., `claude --dangerously-skip-permissions` or `codex --full-auto`). When the consent layer is set to 0, the system relies entirely on Layer 3 (OS Permissions) and Layer 5 (Sandboxing) for safety.

---

### Layer 5: Sandbox / Isolation (Blast Radius Controller)
When Consent Gates are turned off, or when developers approve commands without reviewing them carefully, sandboxing acts as the primary defense boundary.

* **Purpose**: Containment and limiting the blast radius of destructive actions.
* **Mechanisms**:
  * Running the AI CLI agent inside lightweight isolation systems (e.g., **Docker containers**, **Firecracker microVMs**, **WSL (Windows Subsystem for Linux)**, or standard virtual machines).
  * In a sandboxed state, even if the agent executes `rm -rf /` or gets compromised, the damage is restricted to the containerized environment and cannot corrupt the host operating system or steal host credentials.

---

### Layer 6: Local Config & Secrets Leakage
A frequently overlooked risk in AI CLI tooling is the local configuration directory (e.g., `~/.claude/`, `~/.config/claude/`, `~/.codex/`).

* **Purpose**: Local state management and conversation history.
* **Vulnerabilities**:
  * These directories store API keys, OAuth session tokens, cached logs, conversation history (`.jsonl` files), and MCP configurations in plain text.
  * **Risk Vector**: If the developer's machine is compromised by local malware (such as a malicious dependency in another project), the attacker can easily read the plain text configuration files inside `~/.claude/` to steal Anthropic/OpenAI credentials or extract proprietary code from the cached chat logs.

---

## Security Best Practices for AI CLI Execution

To secure local AI agent execution, developers should implement the following mitigations:

1. **Harden Local Directory Permissions**:
   Restrict read/write permissions to the configuration directory so only your user process can access it:
   ```bash
   chmod 700 ~/.claude
   chmod 600 ~/.claude.json
   ```
2. **Execute in Containerized Environments**:
   For untrusted workspaces or complex refactors, run the CLI inside a Docker container:
   ```bash
   docker run -it -v $(pwd):/workspace -w /workspace node:18-slim npx @anthropic-ai/claude-code
   ```
3. **Audit Before Approval**:
   Treat the Consent Gate seriously. Carefully read the proposed commands, file writes, and network operations before pressing `y`.
4. **Use Scoped API Keys**:
   When using custom API keys, configure them with specific spend limits and project scope to minimize financial and access exposure if leaked.
