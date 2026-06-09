# AI Coding Assistants Authentication Reference

This document covers the authentication mechanisms, environment variables, configuration files, and sync methods for **Claude Code** and **Antigravity CLI (`agy`)** across Windows and WSL (Linux) environments.

---

## 1. Claude Code Authentication

Claude Code manages authentication hierarchically, checking credentials in a specific precedence order.

### Precedence of Credentials
1. **Cloud Provider Credentials** (Amazon Bedrock, Google Vertex AI, or Microsoft Azure Foundry)
2. **`ANTHROPIC_AUTH_TOKEN`**: Used for custom gateway/proxy bearer tokens (sends `Authorization: Bearer <token>`).
3. **`ANTHROPIC_API_KEY`**: Standard Anthropic API key for pay-as-you-go billing (sends `x-api-key: <key>`).
4. **`apiKeyHelper`**: A configured shell command in `settings.json` to dynamically retrieve keys.
5. **`CLAUDE_CODE_OAUTH_TOKEN`**: A long-lived OAuth token generated via `claude setup-token` (inference-only).
6. **Subscription Credentials** (OAuth session via browser login `/login`).

### WSL vs Windows Differences
* **Windows:** The default `/login` command uses the native Windows Credential Manager (Keychain) to store OAuth session tokens securely.
* **WSL (Linux):** Since standard Linux keyring services (like `gnome-keyring` or `libsecret`) are not running out-of-the-box in headless WSL, Claude Code falls back to storing active credentials in a file cache at `~/.config/claude-code/` or `~/.claude/`.
* **Important conflict warning:** Windows environment variables can leak into WSL via `WSLENV`. Setting `ANTHROPIC_API_KEY` globally on Windows will leak to WSL, triggering an "Auth conflict" error on Windows. Keep your pay-as-you-go keys local to WSL shell configurations (`.bashrc` / `.zshrc`) or local project `.claude/settings.json`.

---

## 2. Antigravity CLI (`agy`) Authentication

Antigravity CLI (successor to Gemini CLI) is built in Go and utilizes a similar hierarchical credential chain.

### Keyring vs File-based Storage
* **Keyring Precedence:** `agy` natively checks the system's keyring service first (Windows Credential Manager on Windows, Keychain on macOS, or `libsecret`/D-Bus on Linux).
* **File-based Fallback:** If the keyring is inaccessible or cleared, `agy` falls back to reading:
  * Windows: `%USERPROFILE%\.gemini\antigravity-cli\accounts.json`
  * WSL (Linux): `~/.gemini/antigravity-cli/accounts.json`
* **Logout Command:** If Windows has a cached session in the Windows Credential Manager that you want to override (e.g. to switch to a different account), run the following command inside the interactive `agy` CLI:
  ```text
  /logout
  ```
  This clears the Windows Keyring entry, allowing the CLI to fallback and read the active token in the local `accounts.json` file.

---

## 3. The `agyswap` Sync Mechanism

To allow seamless account switching and credential synchronization between WSL and Windows, a wrapper called `agyswap` is provided.

### WSL Alias
`agyswap` wraps the underlying rotation shell script in WSL:
```bash
alias agyswap="~/.gemini/antigravity-cli/agy-rotate.sh"
```

### Windows Wrapper (`agyswap.bat` / `agyswap.ps1`)
To run `agyswap` directly from Windows PowerShell or CMD and keep the Windows `agy.exe` instance in sync with the active WSL session:
1. It delegates the rotation command to WSL using `wsl`.
2. It automatically synchronizes the newly selected credentials back to Windows.

**Implementation of `agyswap.bat`:**
```cmd
@echo off
REM Windows wrapper for agyswap to sync with WSL
wsl ~/.gemini/antigravity-cli/agy-rotate.sh %*
copy /Y \\wsl.localhost\Ubuntu\home\<username>\.gemini\antigravity-cli\accounts.json "%USERPROFILE%\.gemini\antigravity-cli\accounts.json" >nul 2>nul
copy /Y \\wsl.localhost\Ubuntu\home\<username>\.gemini\antigravity-cli\antigravity-oauth-token "%USERPROFILE%\.gemini\antigravity-cli\antigravity-oauth-token" >nul 2>nul
```

---

## 4. Configuration Preservation during `ai-config init`

When running `ai-config init` (which calls the installation script `install.py` with `--force`), the installer preserves active credentials and custom settings in `settings.json` for both tools:

* **Claude Code settings (`.claude/settings.json`):** Preserves `"model"` and custom environment keys in `"env"`:
  * `ANTHROPIC_BASE_URL`
  * `ANTHROPIC_API_KEY`
  * `ANTHROPIC_MODEL`
  * `CLAUDE_CODE_OAUTH_TOKEN`
  * `ANTHROPIC_AUTH_TOKEN`
* **Antigravity CLI settings (`.gemini/antigravity-cli/settings.json`):** Preserves `"model"` and custom environment keys in `"env"`:
  * `GEMINI_API_KEY`
  * `GOOGLE_API_KEY`
  * `ANTHROPIC_API_KEY`
  * `ANTHROPIC_BASE_URL`
  * `ANTHROPIC_AUTH_TOKEN`
