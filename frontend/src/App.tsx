import { useState, useEffect } from 'react';
import { 
  Sliders, LayoutDashboard, Cpu, MessageSquareCode, 
  Terminal as TerminalIcon, Sparkles, Compass
} from 'lucide-react';

import type { FullConfig, CodexConfig } from './types';
import { ToastContainer, type ToastItem } from './components/Toast';
import { Sidebar } from './components/Sidebar';
import { DashboardTab } from './components/DashboardTab';
import { ClaudeTab } from './components/ClaudeTab';
import { McpTab } from './components/McpTab';
import CodexTab from './components/CodexTab';
import GeminiTab from './components/GeminiTab';
import ExplorerTab from './components/ExplorerTab';
import { AddMcpModal, ApplyModal, DiscardModal } from './components/Modals';

const DEFAULT_SERVERS = new Set(["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]);

export default function App() {
  const [initialConfig, setInitialConfig] = useState<FullConfig | null>(null);
  const [tempConfig, setTempConfig] = useState<FullConfig | null>(null);
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [mcpSearch, setMcpSearch] = useState<string>('');
  
  // Explorer states
  const [explorerFilter, setExplorerFilter] = useState<'all' | 'agents' | 'skills'>('all');
  const [selectedExplorer, setSelectedExplorer] = useState<{ type: 'agent' | 'skill'; name: string } | null>(null);

  // MCP Selector
  const [selectedMcpServer, setSelectedMcpServer] = useState<string | null>(null);
  const [showAddMcpModal, setShowAddMcpModal] = useState<boolean>(false);

  // New MCP form states
  const [newMcpName, setNewMcpName] = useState<string>('');
  const [newMcpType, setNewMcpType] = useState<'stdio' | 'sse'>('stdio');
  const [newMcpCommand, setNewMcpCommand] = useState<string>('');
  const [newMcpArgs, setNewMcpArgs] = useState<string>('');
  const [newMcpUrl, setNewMcpUrl] = useState<string>('');
  const [newMcpEnv, setNewMcpEnv] = useState<string>('');
  
  // Log terminal states
  const [logs, setLogs] = useState<string[]>([]);
  
  // Modals state
  const [showApplyModal, setShowApplyModal] = useState<boolean>(false);
  const [showDiscardModal, setShowDiscardModal] = useState<boolean>(false);

  // Toasts
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  // Load config on mount
  useEffect(() => {
    fetchConfig();
  }, []);

  const showToast = (message: string, type: 'success' | 'error' | 'warning' = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (!res.ok) throw new Error("Failed to fetch config");
      const data: FullConfig = await res.json();
      setInitialConfig(data);
      setTempConfig(JSON.parse(JSON.stringify(data)));
      
      // Select first MCP server by default
      if (data.all_mcp.length > 0) {
        setSelectedMcpServer(data.all_mcp[0]);
      }
      
      // Auto-select first explorer item
      if (data.agents.length > 0) {
        setSelectedExplorer({ type: 'agent', name: data.agents[0] });
      } else if (data.skills.length > 0) {
        setSelectedExplorer({ type: 'skill', name: data.skills[0] });
      }
    } catch (err: any) {
      showToast(err.message, 'error');
    }
  };

  if (!tempConfig || !initialConfig) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-base text-blue">
        <div className="flex flex-col items-center gap-4">
          <Sliders className="h-10 w-10 animate-spin" />
          <span className="font-display font-semibold">Loading Config Engine...</span>
        </div>
      </div>
    );
  }

  // --- MUTATION HELPERS ---
  const handleTargetToggle = (cid: string) => {
    setTempConfig(prev => {
      if (!prev) return null;
      return {
        ...prev,
        targets: {
          ...prev.targets,
          [cid]: !prev.targets[cid]
        }
      };
    });
  };

  const handleMcpToggle = (server: string) => {
    setTempConfig(prev => {
      if (!prev) return null;
      let newDisabled = [...prev.disabled_mcp];
      const isCurrentlyEnabled = server in prev.mcp_servers && !newDisabled.includes(server);
      
      if (isCurrentlyEnabled) {
        if (!newDisabled.includes(server)) {
          newDisabled.push(server);
        }
      } else {
        newDisabled = newDisabled.filter(s => s !== server);
      }
      
      return {
        ...prev,
        disabled_mcp: newDisabled,
        mcp_servers: {
          ...prev.mcp_servers,
          [server]: prev.mcp_servers[server] || {}
        }
      };
    });
  };

  const batchMcp = (enableAll: boolean) => {
    setTempConfig(prev => {
      if (!prev) return null;
      let newDisabled = [...prev.disabled_mcp];
      
      prev.all_mcp.forEach(server => {
        if (enableAll) {
          newDisabled = newDisabled.filter(s => s !== server);
        } else {
          if (!newDisabled.includes(server)) {
            newDisabled.push(server);
          }
        }
      });
      
      return {
        ...prev,
        disabled_mcp: newDisabled
      };
    });
  };

  const handleClaudeEnvChange = (key: string, value: string) => {
    setTempConfig(prev => {
      if (!prev) return null;
      const env = { ...prev.claude.env, [key]: value };
      return {
        ...prev,
        claude: { ...prev.claude, env }
      };
    });
  };

  const handleClaudePermsChange = (key: string, value: string) => {
    setTempConfig(prev => {
      if (!prev) return null;
      const permissions = { ...prev.claude.permissions, [key]: value };
      return {
        ...prev,
        claude: { ...prev.claude, permissions }
      };
    });
  };

  const addCustomMcp = () => {
    const name = newMcpName.trim().toLowerCase();
    if (!name) {
      showToast("Server name is required", "error");
      return;
    }
    if (tempConfig.all_mcp.includes(name)) {
      showToast(`Server "${name}" already exists`, "error");
      return;
    }
    
    let envObj: Record<string, string> = {};
    if (newMcpEnv.trim()) {
      try {
        envObj = JSON.parse(newMcpEnv);
      } catch (e) {
        showToast("Invalid Environment JSON", "error");
        return;
      }
    }
    
    const argsArr = newMcpArgs.split('\n').map(a => a.trim()).filter(Boolean);
    const serverConfig: any = {};
    if (newMcpType === 'sse') {
      serverConfig.type = 'sse';
      serverConfig.url = newMcpUrl.trim();
    } else {
      serverConfig.command = newMcpCommand.trim();
      if (argsArr.length > 0) serverConfig.args = argsArr;
      if (Object.keys(envObj).length > 0) serverConfig.env = envObj;
    }
    
    setTempConfig(prev => {
      if (!prev) return null;
      return {
        ...prev,
        all_mcp: [...prev.all_mcp, name],
        mcp_servers: {
          ...prev.mcp_servers,
          [name]: serverConfig
        }
      };
    });
    
    setSelectedMcpServer(name);
    setShowAddMcpModal(false);
    
    // Clear form fields
    setNewMcpName('');
    setNewMcpCommand('');
    setNewMcpArgs('');
    setNewMcpUrl('');
    setNewMcpEnv('');
    
    showToast(`Custom MCP server "${name}" added to staging!`, "success");
  };

  const deleteCustomMcp = (name: string) => {
    if (DEFAULT_SERVERS.has(name)) return;
    
    setTempConfig(prev => {
      if (!prev) return null;
      const { [name]: removed, ...restServers } = prev.mcp_servers;
      return {
        ...prev,
        all_mcp: prev.all_mcp.filter(s => s !== name),
        disabled_mcp: prev.disabled_mcp.filter(s => s !== name),
        mcp_servers: restServers
      };
    });
    
    // Select another server
    const remaining = tempConfig.all_mcp.filter(s => s !== name);
    if (remaining.length > 0) {
      setSelectedMcpServer(remaining[0]);
    } else {
      setSelectedMcpServer(null);
    }
    
    showToast(`MCP server "${name}" removed!`, "warning");
  };

  // --- DIFF COMPUTATION ---
  const getPendingChanges = () => {
    const diffs: Array<{ key: string; text: string; type: 'add' | 'remove' | 'mod' }> = [];
    
    // 1. Targets
    for (const [cid, name] of Object.entries({ claude: 'Claude Code', codex: 'Codex CLI', agy: 'Antigravity' })) {
      if (initialConfig.targets[cid] !== tempConfig.targets[cid]) {
        diffs.push({
          key: `target-${cid}`,
          text: `Target ${name}: → ${tempConfig.targets[cid] ? 'Install' : 'Exclude'}`,
          type: tempConfig.targets[cid] ? 'add' : 'remove'
        });
      }
    }
    
    // 2. MCP toggles
    tempConfig.all_mcp.forEach(server => {
      const initDisabled = initialConfig.disabled_mcp.includes(server);
      const initEnabled = server in initialConfig.mcp_servers && !initDisabled;
      
      const tempDisabled = tempConfig.disabled_mcp.includes(server);
      const tempEnabled = server in tempConfig.mcp_servers && !tempDisabled;
      
      if (initEnabled !== tempEnabled) {
        diffs.push({
          key: `mcp-${server}`,
          text: `MCP ${server}: → ${tempEnabled ? 'Enable' : 'Disable'}`,
          type: tempEnabled ? 'add' : 'remove'
        });
      }
    });

    // 2b. MCP configurations
    tempConfig.all_mcp.forEach(server => {
      const initS = initialConfig.mcp_servers[server];
      const tempS = tempConfig.mcp_servers[server];
      if (!initS && tempS) {
        diffs.push({
          key: `mcp-config-add-${server}`,
          text: `MCP Config: Add custom server "${server}"`,
          type: 'add'
        });
      } else if (initS && !tempS) {
        diffs.push({
          key: `mcp-config-del-${server}`,
          text: `MCP Config: Remove custom server "${server}"`,
          type: 'remove'
        });
      } else if (initS && tempS) {
        const initStr = JSON.stringify(initS);
        const tempStr = JSON.stringify(tempS);
        if (initStr !== tempStr) {
          diffs.push({
            key: `mcp-config-mod-${server}`,
            text: `MCP Config "${server}": settings updated`,
            type: 'mod'
          });
        }
      }
    });
    
    // 3. Claude Settings
    const envInit = initialConfig.claude.env || {};
    const envTemp = tempConfig.claude.env || {};
    for (const k of ["MAX_THINKING_TOKENS", "CLAUDE_CODE_MAX_OUTPUT_TOKENS", "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE", "CLAUDE_CODE_NO_FLICKER"]) {
      if (envInit[k] !== envTemp[k]) {
        diffs.push({
          key: `claude-env-${k}`,
          text: `Claude ${k}: ${envInit[k] || 'None'} → ${envTemp[k] || 'None'}`,
          type: 'mod'
        });
      }
    }
    
    const permsInit = initialConfig.claude.permissions || {};
    const permsTemp = tempConfig.claude.permissions || {};
    if (permsInit.defaultMode !== permsTemp.defaultMode) {
      diffs.push({
        key: 'claude-perm-mode',
        text: `Claude Mode: ${permsInit.defaultMode || 'None'} → ${permsTemp.defaultMode || 'None'}`,
        type: 'mod'
      });
    }
    
    if (initialConfig.claude.skipDangerousModePermissionPrompt !== tempConfig.claude.skipDangerousModePermissionPrompt) {
      diffs.push({
        key: 'claude-skip-prompt',
        text: `Claude Skip Prompt: ${initialConfig.claude.skipDangerousModePermissionPrompt} → ${tempConfig.claude.skipDangerousModePermissionPrompt}`,
        type: 'mod'
      });
    }
    
    // 4. Codex Settings
    const fields: Array<keyof CodexConfig> = ["approval_policy", "sandbox_mode", "web_search", "approvals_reviewer", "model", "model_reasoning_effort", "persistent_instructions"];
    fields.forEach(k => {
      if (initialConfig.codex[k] !== tempConfig.codex[k]) {
        diffs.push({
          key: `codex-${k}`,
          text: `Codex ${k}: ${initialConfig.codex[k] || 'None'} → ${tempConfig.codex[k] || 'None'}`,
          type: 'mod'
        });
      }
    });
    
    const featInit = initialConfig.codex.features || {};
    const featTemp = tempConfig.codex.features || {};
    for (const k of ["memories", "multi_agent"] as Array<keyof Required<CodexConfig>['features']>) {
      if (featInit[k] !== featTemp[k]) {
        diffs.push({
          key: `codex-feat-${k}`,
          text: `Codex Feature ${k}: ${featInit[k]} → ${featTemp[k]}`,
          type: 'mod'
        });
      }
    }
    
    const notInit = initialConfig.codex.notice || {};
    const notTemp = tempConfig.codex.notice || {};
    for (const k of ["hide_full_access_warning", "fast_default_opt_out"] as Array<keyof Required<CodexConfig>['notice']>) {
      if (notInit[k] !== notTemp[k]) {
        diffs.push({
          key: `codex-notice-${k}`,
          text: `Codex Notice ${k}: ${notInit[k]} → ${notTemp[k]}`,
          type: 'mod'
        });
      }
    }

    // 4b. Gemini Settings
    const geminiInit = initialConfig.gemini || {};
    const geminiTemp = tempConfig.gemini || {};
    if (geminiInit.enableTelemetry !== geminiTemp.enableTelemetry) {
      diffs.push({
        key: 'gemini-telemetry',
        text: `Gemini Telemetry: ${geminiInit.enableTelemetry} → ${geminiTemp.enableTelemetry}`,
        type: 'mod'
      });
    }
    if (geminiInit.model !== geminiTemp.model) {
      diffs.push({
        key: 'gemini-model',
        text: `Gemini Model: ${geminiInit.model || 'None'} → ${geminiTemp.model || 'None'}`,
        type: 'mod'
      });
    }
    if (geminiInit.toolPermission !== geminiTemp.toolPermission) {
      diffs.push({
        key: 'gemini-tool-permission',
        text: `Gemini Tool Permission: ${geminiInit.toolPermission || 'None'} → ${geminiTemp.toolPermission || 'None'}`,
        type: 'mod'
      });
    }
    const initWorkspaces = JSON.stringify(geminiInit.trustedWorkspaces || []);
    const tempWorkspaces = JSON.stringify(geminiTemp.trustedWorkspaces || []);
    if (initWorkspaces !== tempWorkspaces) {
      diffs.push({
        key: 'gemini-workspaces',
        text: `Gemini Trusted Workspaces: (Modified)`,
        type: 'mod'
      });
    }
    
    // 5. Instruction Files (.md files)

    if (initialConfig.gemini_instructions !== tempConfig.gemini_instructions) {
      diffs.push({
        key: 'gemini-instructions',
        text: `~ Antigravity Instructions (ANTIGRAVITY.md): (Modified)`,
        type: 'mod'
      });
    }

    if (initialConfig.claude_instructions !== tempConfig.claude_instructions) {
      diffs.push({
        key: 'claude-instructions',
        text: `~ Claude Instructions (CLAUDE.md): (Modified)`,
        type: 'mod'
      });
    }

    if (initialConfig.codex_instructions !== tempConfig.codex_instructions) {
      diffs.push({
        key: 'codex-instructions',
        text: `~ Codex Instructions (AGENTS.md): (Modified)`,
        type: 'mod'
      });
    }
    
    return diffs;
  };

  const pendingChanges = getPendingChanges();
  const hasPendingChanges = pendingChanges.length > 0;

  // --- ACTIONS ---
  const executeDiscard = () => {
    setTempConfig(JSON.parse(JSON.stringify(initialConfig)));
    setShowDiscardModal(false);
    showToast("Staged changes reverted!", "warning");
  };

  const executeApply = async (force: boolean) => {
    setShowApplyModal(false);
    setActiveTab('dashboard');
    setLogs(["🚀 Connecting to installation log stream...", "✓ Settings templates written. Running installation..."]);
    
    try {
      // 1. Send staging configs to save-temp
      const saveRes = await fetch('/api/save-temp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claude: tempConfig.claude,
          codex: tempConfig.codex,
          gemini: tempConfig.gemini,
          disabled_mcp: tempConfig.disabled_mcp,
          mcp_servers: tempConfig.mcp_servers,
          gemini_instructions: tempConfig.gemini_instructions,
          claude_instructions: tempConfig.claude_instructions,
          codex_instructions: tempConfig.codex_instructions
        })
      });
      
      if (!saveRes.ok) {
        const errJson = await saveRes.json();
        throw new Error(errJson.detail || "Failed to save settings");
      }
      
      // 2. Open Server-Sent Events stream
      const sseUrl = `/api/apply/stream?force=${force}&claude=${tempConfig.targets.claude}&codex=${tempConfig.targets.codex}&agy=${tempConfig.targets.agy}`;
      const eventSource = new EventSource(sseUrl);
      
      eventSource.onmessage = (event) => {
        const line = event.data;
        setLogs(prev => [...prev, line]);
        
        if (line.includes("SUCCESS:") || line.includes("ERROR:")) {
          eventSource.close();
          // Reload configs to get absolute fresh initial state
          fetchConfig();
        }
      };
      
      eventSource.onerror = (err: any) => {
        console.error("SSE error:", err);
        setLogs(prev => [...prev, "✘ Connection to log stream lost. Process may still be running."]);
        eventSource.close();
        fetchConfig();
      };
      
    } catch (err: any) {
      setLogs(prev => [...prev, `✘ Error: ${err.message}`]);
      showToast(`Apply failed: ${err.message}`, 'error');
    }
  };

  // Filter MCP list
  const filteredMcp = tempConfig.all_mcp.filter(s => s.toLowerCase().includes(mcpSearch.toLowerCase()));

  // Map pending changes type signature for Sidebar compatibility
  const mappedPendingChanges = pendingChanges.map(c => ({
    key: c.key,
    text: c.text,
    type: c.type === 'remove' ? 'del' as const : c.type
  }));

  return (
    <div className="flex w-screen h-screen overflow-hidden bg-base text-text selection:bg-surface2">
      
      {/* SIDEBAR */}
      <Sidebar 
        initialConfig={initialConfig}
        tempConfig={tempConfig}
        handleTargetToggle={handleTargetToggle}
        handleMcpToggle={handleMcpToggle}
        batchMcp={batchMcp}
        mcpSearch={mcpSearch}
        setMcpSearch={setMcpSearch}
        filteredMcp={filteredMcp}
        hasPendingChanges={hasPendingChanges}
        pendingChanges={mappedPendingChanges}
        setShowApplyModal={setShowApplyModal}
        setShowDiscardModal={setShowDiscardModal}
      />

      {/* MAIN VIEW */}
      <main className="flex-1 flex flex-col h-full bg-base overflow-hidden">
        
        {/* Tab Headers */}
        <header className="flex bg-mantle border-b border-surface0 px-8 items-center justify-between">
          <div className="flex gap-1">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
              { id: 'mcp', label: 'MCP Settings', icon: Cpu },
              { id: 'claude', label: 'Claude Code', icon: MessageSquareCode },
              { id: 'codex', label: 'Codex CLI', icon: TerminalIcon },
              { id: 'gemini', label: 'Antigravity CLI', icon: Sparkles },
              { id: 'explorer', label: 'Agents & Skills', icon: Compass }
            ].map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 py-5 px-4 text-xs font-semibold font-display border-b-3 transition-all duration-200 cursor-pointer ${
                    active ? 'text-blue border-blue' : 'text-overlay2 border-transparent hover:text-text'
                  }`}
                >
                  <Icon className="h-4 w-4" /> {tab.label}
                </button>
              );
            })}
          </div>
          <span className="text-[11px] text-overlay1 bg-surface0 border border-surface1 px-2.5 py-1 rounded-full font-mono">
            Vite React App
          </span>
        </header>

        {/* Tab Contents */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* TAB 1: DASHBOARD */}
          {activeTab === 'dashboard' && (
            <DashboardTab 
              tempConfig={tempConfig}
              logs={logs}
              setLogs={setLogs}
              setActiveTab={setActiveTab}
              setExplorerFilter={setExplorerFilter}
              setSelectedExplorer={setSelectedExplorer}
            />
          )}

          {/* TAB 2: MCP SETTINGS TAB */}
          {activeTab === 'mcp' && (
            <McpTab 
              tempConfig={tempConfig}
              setTempConfig={setTempConfig}
              selectedMcpServer={selectedMcpServer}
              setSelectedMcpServer={setSelectedMcpServer}
              filteredMcp={filteredMcp}
              mcpSearch={mcpSearch}
              setMcpSearch={setMcpSearch}
              handleMcpToggle={handleMcpToggle}
              deleteCustomMcp={deleteCustomMcp}
              setShowAddMcpModal={setShowAddMcpModal}
              showToast={showToast}
            />
          )}

          {/* TAB 3: CLAUDE SETTINGS */}
          {activeTab === 'claude' && (
            <ClaudeTab 
              initialConfig={initialConfig}
              tempConfig={tempConfig}
              setTempConfig={setTempConfig}
              handleClaudeEnvChange={handleClaudeEnvChange}
              handleClaudePermsChange={handleClaudePermsChange}
            />
          )}

          {/* TAB 4: CODEX SETTINGS */}
          {activeTab === 'codex' && (
            <CodexTab 
              initialConfig={initialConfig}
              tempConfig={tempConfig}
              setTempConfig={setTempConfig}
            />
          )}

          {/* TAB 5: ANTIGRAVITY INSTRUCTIONS */}
          {activeTab === 'gemini' && (
            <GeminiTab 
              initialConfig={initialConfig}
              tempConfig={tempConfig}
              setTempConfig={setTempConfig}
            />
          )}

          {/* TAB 6: AGENTS & SKILLS EXPLORER */}
          {activeTab === 'explorer' && (
            <ExplorerTab 
              tempConfig={tempConfig}
              selectedExplorer={selectedExplorer}
              setSelectedExplorer={setSelectedExplorer}
              showToast={showToast}
              explorerFilter={explorerFilter}
              setExplorerFilter={setExplorerFilter}
            />
          )}

        </div>
      </main>

      {/* TOASTS PORTAL */}
      <ToastContainer toasts={toasts} />

      {/* MODALS */}
      <AddMcpModal 
        isOpen={showAddMcpModal}
        onClose={() => setShowAddMcpModal(false)}
        newMcpName={newMcpName}
        setNewMcpName={setNewMcpName}
        newMcpType={newMcpType}
        setNewMcpType={setNewMcpType}
        newMcpCommand={newMcpCommand}
        setNewMcpCommand={setNewMcpCommand}
        newMcpArgs={newMcpArgs}
        setNewMcpArgs={setNewMcpArgs}
        newMcpEnv={newMcpEnv}
        setNewMcpEnv={setNewMcpEnv}
        newMcpUrl={newMcpUrl}
        setNewMcpUrl={setNewMcpUrl}
        onAdd={addCustomMcp}
      />

      <ApplyModal 
        isOpen={showApplyModal}
        onClose={() => setShowApplyModal(false)}
        onApply={executeApply}
      />

      <DiscardModal 
        isOpen={showDiscardModal}
        onClose={() => setShowDiscardModal(false)}
        onDiscard={executeDiscard}
      />

    </div>
  );
}
