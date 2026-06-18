# Security Best Practices Review & Scan Report

**Project:** `ai-coding-config` / `agy`  
**Date:** June 17, 2026  
**Auditor:** Antigravity AI  

---

## Executive Summary

A comprehensive security scan and codebase audit was performed using Graphify analysis and security best practice guidelines. The scan focused on local HTTP endpoints, subprocess execution, credential storage, path validation, and file permissions.

All identified vulnerabilities have been successfully resolved using a strict Test-Driven Development (TDD) workflow:
- **SEC-001 (File Permissions)**: Enforced strict `0o600` permissions on all OAuth token and configuration writes.
- **SEC-002 (Unauthenticated Command Execution)**: Secured the simulator execution endpoint with a startup-generated random session token checked via Headers/Cookies.
- **SEC-003 (Local File Inclusion)**: Restricted file serving to safe directories using the `is_safe_path()` resolver.

---

## Detailed Findings & Resolution Status

### SEC-001: Inconsistent File Permissions on Sensitive Token and Configuration Writes (Medium)

- **Severity:** Medium
- **Status:** ✅ Resolved (Fixed on June 17, 2026)
- **Target Files:** 
  - [tools/agy/switch.py](tools/agy/switch.py)
  - [backend/mcp_manager.py](backend/mcp_manager.py)

#### Impact Statement
OAuth credentials and configuration files containing system paths and server secrets can be created with world-readable permissions (e.g. `0644`), exposing credentials to other local users on the same machine.

#### Resolution Details
Implemented strict `0o600` permission enforcement. Whenever `switch.py` writes the `TOKEN_FILE` or updates the accounts database (`JSON_FILE`), and whenever `mcp_manager.py` updates client configurations (`~/.claude.json`, `~/.gemini/config/mcp_config.json`, and `~/.codex/config.toml`), `os.chmod(..., 0o600)` is applied on POSIX systems immediately after writing. Unit tests were added in `tests/test_switch.py` and `tests/test_security.py` to assert correct permission modes.

---

### SEC-002: Unauthenticated Arbitrary Command Execution via Local HTTP Endpoint (Critical)

- **Severity:** Critical
- **Status:** ✅ Resolved (Fixed on June 17, 2026)
- **Target Files:**
  - [server.py](server.py)
  - [backend/handler.py](backend/handler.py)

#### Impact Statement
A local attacker or malicious application can send unauthenticated HTTP POST requests to `/api/simulator/execute` to run arbitrary shell commands on the host under the server user's privileges.

#### Resolution Details
Implemented a secure session token authentication scheme. The server generates a random, cryptographically secure 32-byte hex token on startup. The endpoint `/api/simulator/execute` validates that this token is provided in the `X-Session-Token` or `Authorization: Bearer` headers, or inside the browser `session_token` cookie. The cookie is automatically set on clients via a secure `Set-Cookie` header when loading HTML pages (like `index.html`), ensuring seamless frontend integration with zero client modifications.

---

### SEC-003: Unauthenticated Sensitive File Read / Local File Inclusion (Critical)

- **Severity:** Critical
- **Status:** ✅ Resolved (Fixed on June 17, 2026)
- **Target File:** [backend/handler.py](backend/handler.py)

#### Impact Statement
An unauthenticated local attacker or malicious website (via DNS rebinding) can read sensitive credentials like Google OAuth tokens and client databases directly via static HTTP GET routes.

#### Description
In `_serve_static_resources`, the handler checks if a URL path contains sensitive keywords like `".gemini"` or `".claude"`. If it does, it dynamically resolves the path to the user's home directory (`Path.home() / unquoted_path`) and returns the raw file contents (e.g. `/api/.gemini/antigravity-cli/accounts.json`), bypassing all sandbox directory boundaries.

#### Resolution Details
Developed and integrated a directory traversal validator helper `is_safe_path(path, allowed_bases)`. When static resources or media files are requested, the resolved canonical absolute path is verified to ensure it is nested under safe directories (the repository workspace root and explicit application configuration folders). Safe path unit tests were implemented in `tests/test_security.py`.
