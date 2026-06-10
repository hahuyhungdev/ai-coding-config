import { useState, useEffect, useCallback } from 'react';
import type { FullConfig, CodexConfig } from '../types';

const DEFAULT_SERVERS = new Set(["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]);

export interface PendingChange {
  key: string;
  text: string;
  type: 'add' | 'remove' | 'mod';
}

export function useConfig(showToast: (msg: string, type?: 'success' | 'error' | 'warning') => void) {
  const [initialConfig, setInitialConfig] = useState<FullConfig | null>(null);
  const [tempConfig, setTempConfig] = useState<FullConfig | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) throw new Error("Failed to fetch config");
      const data: FullConfig = await res.json();
      setInitialConfig(data);
      setTempConfig(JSON.parse(JSON.stringify(data)));
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  }, [showToast]);

  useEffect(() => { fetchConfig(); }, [fetchConfig]);

  // --- MUTATION HELPERS ---
  const handleTargetToggle = useCallback((cid: string) => {
    setTempConfig(prev => prev ? { ...prev, targets: { ...prev.targets, [cid]: !prev.targets[cid] } } : null);
  }, []);

  const handleMcpToggle = useCallback((server: string) => {
    setTempConfig(prev => {
      if (!prev) return null;
      let newDisabled = [...prev.disabled_mcp];
      const isCurrentlyEnabled = server in prev.mcp_servers && !newDisabled.includes(server);
      if (isCurrentlyEnabled) {
        if (!newDisabled.includes(server)) newDisabled.push(server);
      } else {
        newDisabled = newDisabled.filter(s => s !== server);
      }
      return { ...prev, disabled_mcp: newDisabled, mcp_servers: { ...prev.mcp_servers, [server]: prev.mcp_servers[server] || {} } };
    });
  }, []);

  const batchMcp = useCallback((enableAll: boolean) => {
    setTempConfig(prev => {
      if (!prev) return null;
      let newDisabled = [...prev.disabled_mcp];
      prev.all_mcp.forEach(server => {
        if (enableAll) {
          newDisabled = newDisabled.filter(s => s !== server);
        } else if (!newDisabled.includes(server)) {
          newDisabled.push(server);
        }
      });
      return { ...prev, disabled_mcp: newDisabled };
    });
  }, []);

  const handleClaudeEnvChange = useCallback((key: string, value: string) => {
    setTempConfig(prev => prev ? { ...prev, claude: { ...prev.claude, env: { ...prev.claude.env, [key]: value } } } : null);
  }, []);

  const handleClaudePermsChange = useCallback((key: string, value: string) => {
    setTempConfig(prev => prev ? { ...prev, claude: { ...prev.claude, permissions: { ...prev.claude.permissions, [key]: value } } } : null);
  }, []);

  const deleteCustomMcp = useCallback((name: string, setSelectedMcpServer: (s: string | null) => void) => {
    if (DEFAULT_SERVERS.has(name)) return;
    setTempConfig(prev => {
      if (!prev) return null;
      const { [name]: removed, ...restServers } = prev.mcp_servers;
      return { ...prev, all_mcp: prev.all_mcp.filter(s => s !== name), disabled_mcp: prev.disabled_mcp.filter(s => s !== name), mcp_servers: restServers };
    });
    if (tempConfig) {
      const remaining = tempConfig.all_mcp.filter(s => s !== name);
      setSelectedMcpServer(remaining.length > 0 ? remaining[0] : null);
    }
    showToast(`MCP server "${name}" removed!`, "warning");
  }, [tempConfig, showToast]);

  // --- DIFF COMPUTATION ---
  const getPendingChanges = useCallback((): PendingChange[] => {
    if (!initialConfig || !tempConfig) return [];
    const diffs: PendingChange[] = [];

    // 1. Targets
    for (const [cid, name] of Object.entries({ claude: 'Claude Code', codex: 'Codex CLI', agy: 'Antigravity' })) {
      if (initialConfig.targets[cid] !== tempConfig.targets[cid]) {
        diffs.push({ key: `target-${cid}`, text: `Target ${name}: → ${tempConfig.targets[cid] ? 'Install' : 'Exclude'}`, type: tempConfig.targets[cid] ? 'add' : 'remove' });
      }
    }

    // 2. MCP toggles
    tempConfig.all_mcp.forEach(server => {
      const initEnabled = server in initialConfig.mcp_servers && !initialConfig.disabled_mcp.includes(server);
      const tempEnabled = server in tempConfig.mcp_servers && !tempConfig.disabled_mcp.includes(server);
      if (initEnabled !== tempEnabled) {
        diffs.push({ key: `mcp-${server}`, text: `MCP ${server}: → ${tempEnabled ? 'Enable' : 'Disable'}`, type: tempEnabled ? 'add' : 'remove' });
      }
    });

    // 2b. MCP configurations
    tempConfig.all_mcp.forEach(server => {
      const initS = initialConfig.mcp_servers[server];
      const tempS = tempConfig.mcp_servers[server];
      if (!initS && tempS) diffs.push({ key: `mcp-config-add-${server}`, text: `MCP Config: Add custom server "${server}"`, type: 'add' });
      else if (initS && !tempS) diffs.push({ key: `mcp-config-del-${server}`, text: `MCP Config: Remove custom server "${server}"`, type: 'remove' });
      else if (initS && tempS && JSON.stringify(initS) !== JSON.stringify(tempS)) diffs.push({ key: `mcp-config-mod-${server}`, text: `MCP Config "${server}": settings updated`, type: 'mod' });
    });

    // 3. Claude Settings
    const envInit = initialConfig.claude.env || {};
    const envTemp = tempConfig.claude.env || {};
    for (const k of ["MAX_THINKING_TOKENS", "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_CODE_NO_FLICKER"]) {
      if (envInit[k] !== envTemp[k]) diffs.push({ key: `claude-env-${k}`, text: `Claude ${k}: ${envInit[k] || 'None'} → ${envTemp[k] || 'None'}`, type: 'mod' });
    }
    if ((initialConfig.claude.permissions || {}).defaultMode !== (tempConfig.claude.permissions || {}).defaultMode) {
      diffs.push({ key: 'claude-perm-mode', text: `Claude Mode: ${(initialConfig.claude.permissions || {}).defaultMode || 'None'} → ${(tempConfig.claude.permissions || {}).defaultMode || 'None'}`, type: 'mod' });
    }
    if (initialConfig.claude.skipDangerousModePermissionPrompt !== tempConfig.claude.skipDangerousModePermissionPrompt) {
      diffs.push({ key: 'claude-skip-prompt', text: `Claude Skip Prompt: ${initialConfig.claude.skipDangerousModePermissionPrompt} → ${tempConfig.claude.skipDangerousModePermissionPrompt}`, type: 'mod' });
    }

    // 4. Codex Settings
    const fields: Array<keyof CodexConfig> = ["approval_policy", "sandbox_mode", "web_search", "approvals_reviewer", "model", "model_reasoning_effort", "persistent_instructions"];
    fields.forEach(k => {
      if (initialConfig.codex[k] !== tempConfig.codex[k]) diffs.push({ key: `codex-${k}`, text: `Codex ${k}: ${initialConfig.codex[k] || 'None'} → ${tempConfig.codex[k] || 'None'}`, type: 'mod' });
    });
    for (const k of ["memories", "multi_agent"] as Array<keyof Required<CodexConfig>['features']>) {
      if ((initialConfig.codex.features || {})[k] !== (tempConfig.codex.features || {})[k]) diffs.push({ key: `codex-feat-${k}`, text: `Codex Feature ${k}: ${(initialConfig.codex.features || {})[k]} → ${(tempConfig.codex.features || {})[k]}`, type: 'mod' });
    }
    for (const k of ["hide_full_access_warning", "fast_default_opt_out"] as Array<keyof Required<CodexConfig>['notice']>) {
      if ((initialConfig.codex.notice || {})[k] !== (tempConfig.codex.notice || {})[k]) diffs.push({ key: `codex-notice-${k}`, text: `Codex Notice ${k}: ${(initialConfig.codex.notice || {})[k]} → ${(tempConfig.codex.notice || {})[k]}`, type: 'mod' });
    }

    // 4b. Gemini Settings
    const geminiInit = initialConfig.gemini || {};
    const geminiTemp = tempConfig.gemini || {};
    if (geminiInit.enableTelemetry !== geminiTemp.enableTelemetry) diffs.push({ key: 'gemini-telemetry', text: `Gemini Telemetry: ${geminiInit.enableTelemetry} → ${geminiTemp.enableTelemetry}`, type: 'mod' });
    if (geminiInit.model !== geminiTemp.model) diffs.push({ key: 'gemini-model', text: `Gemini Model: ${geminiInit.model || 'None'} → ${geminiTemp.model || 'None'}`, type: 'mod' });
    if (geminiInit.toolPermission !== geminiTemp.toolPermission) diffs.push({ key: 'gemini-tool-permission', text: `Gemini Tool Permission: ${geminiInit.toolPermission || 'None'} → ${geminiTemp.toolPermission || 'None'}`, type: 'mod' });
    if (JSON.stringify(geminiInit.trustedWorkspaces || []) !== JSON.stringify(geminiTemp.trustedWorkspaces || [])) diffs.push({ key: 'gemini-workspaces', text: `Gemini Trusted Workspaces: (Modified)`, type: 'mod' });

    // 5. Instruction Files
    if (initialConfig.gemini_instructions !== tempConfig.gemini_instructions) diffs.push({ key: 'gemini-instructions', text: `~ Antigravity Instructions (ANTIGRAVITY.md): (Modified)`, type: 'mod' });
    if (initialConfig.claude_instructions !== tempConfig.claude_instructions) diffs.push({ key: 'claude-instructions', text: `~ Claude Instructions (CLAUDE.md): (Modified)`, type: 'mod' });
    if (initialConfig.codex_instructions !== tempConfig.codex_instructions) diffs.push({ key: 'codex-instructions', text: `~ Codex Instructions (AGENTS.md): (Modified)`, type: 'mod' });

    return diffs;
  }, [initialConfig, tempConfig]);

  // --- ACTIONS ---
  const executeDiscard = useCallback(() => {
    if (!initialConfig) return;
    setTempConfig(JSON.parse(JSON.stringify(initialConfig)));
    showToast("Staged changes reverted!", "warning");
  }, [initialConfig, showToast]);

  const executeApply = useCallback(async (force: boolean, targets: { claude: boolean; codex: boolean; agy: boolean }) => {
    if (!tempConfig) return;
    setLogs(["🚀 Connecting to installation log stream...", "✓ Settings templates written. Running installation..."]);
    try {
      const saveRes = await fetch('/api/save-temp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claude: tempConfig.claude, codex: tempConfig.codex, gemini: tempConfig.gemini,
          disabled_mcp: tempConfig.disabled_mcp, mcp_servers: tempConfig.mcp_servers,
          gemini_instructions: tempConfig.gemini_instructions, claude_instructions: tempConfig.claude_instructions, codex_instructions: tempConfig.codex_instructions
        })
      });
      if (!saveRes.ok) { const errJson = await saveRes.json(); throw new Error(errJson.detail || "Failed to save settings"); }

      const sseUrl = `/api/apply/stream?force=${force}&claude=${targets.claude}&codex=${targets.codex}&agy=${targets.agy}`;
      const eventSource = new EventSource(sseUrl);
      eventSource.onmessage = (event) => {
        setLogs(prev => [...prev, event.data]);
        if (event.data.includes("SUCCESS:") || event.data.includes("ERROR:")) { eventSource.close(); fetchConfig(); }
      };
      eventSource.onerror = () => { setLogs(prev => [...prev, "✘ Connection to log stream lost."]); eventSource.close(); fetchConfig(); };
    } catch (err: any) {
      setLogs(prev => [...prev, `✘ Error: ${err.message}`]);
      showToast(`Apply failed: ${err.message}`, 'error');
    }
  }, [tempConfig, fetchConfig, showToast]);

  return {
    initialConfig, tempConfig, setTempConfig, logs, setLogs,
    fetchConfig, handleTargetToggle, handleMcpToggle, batchMcp,
    handleClaudeEnvChange, handleClaudePermsChange, deleteCustomMcp,
    getPendingChanges, executeDiscard, executeApply
  };
}
