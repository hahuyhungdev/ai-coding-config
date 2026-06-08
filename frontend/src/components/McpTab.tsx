import React, { useState, useEffect } from 'react';
import type { FullConfig } from '../types';
import { Toggle } from './Toggle';
import { 
  Search, Plus, Cpu, Play, Save, Trash as TrashIcon, 
  CheckCircle2, AlertTriangle, XCircle, Sliders 
} from 'lucide-react';

interface McpTabProps {
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  selectedMcpServer: string | null;
  setSelectedMcpServer: (server: string | null) => void;
  filteredMcp: string[];
  mcpSearch: string;
  setMcpSearch: (val: string) => void;
  handleMcpToggle: (server: string) => void;
  deleteCustomMcp: (server: string) => void;
  setShowAddMcpModal: (show: boolean) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'warning') => void;
}

const DEFAULT_SERVERS = new Set(["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]);

export const McpTab: React.FC<McpTabProps> = ({
  tempConfig,
  setTempConfig,
  selectedMcpServer,
  setSelectedMcpServer,
  filteredMcp,
  mcpSearch,
  setMcpSearch,
  handleMcpToggle,
  deleteCustomMcp,
  setShowAddMcpModal,
  showToast
}) => {
  // Local editor states
  const [mcpEditorType, setMcpEditorType] = useState<'stdio' | 'sse'>('stdio');
  const [mcpEditorCommand, setMcpEditorCommand] = useState<string>('');
  const [mcpEditorArgs, setMcpEditorArgs] = useState<string>('');
  const [mcpEditorUrl, setMcpEditorUrl] = useState<string>('');
  const [mcpEditorEnv, setMcpEditorEnv] = useState<string>('');
  const [mcpTestStatus, setMcpTestStatus] = useState<'idle' | 'testing' | 'success' | 'error' | 'warning'>('idle');
  const [mcpTestMessage, setMcpTestMessage] = useState<string>('');

  // Sync MCP editor fields when selected server changes
  useEffect(() => {
    setMcpTestStatus('idle');
    setMcpTestMessage('');
    if (selectedMcpServer && tempConfig) {
      const config = tempConfig.mcp_servers[selectedMcpServer] || {};
      const isSse = config.type === 'sse' || !!config.url;
      setMcpEditorType(isSse ? 'sse' : 'stdio');
      setMcpEditorCommand(config.command || '');
      setMcpEditorUrl(config.url || '');
      
      if (Array.isArray(config.args)) {
        setMcpEditorArgs(config.args.join('\n'));
      } else {
        setMcpEditorArgs(config.args ? String(config.args) : '');
      }
      
      if (config.env) {
        setMcpEditorEnv(JSON.stringify(config.env, null, 2));
      } else {
        setMcpEditorEnv('');
      }
    }
  }, [selectedMcpServer, tempConfig]);

  const saveMcpEditor = () => {
    if (!selectedMcpServer) return;
    
    let envObj: Record<string, string> = {};
    if (mcpEditorEnv.trim()) {
      try {
        envObj = JSON.parse(mcpEditorEnv);
      } catch (e) {
        showToast("Invalid Environment JSON. Please verify syntax.", "error");
        return;
      }
    }
    
    const argsArr = mcpEditorArgs.split('\n').map(a => a.trim()).filter(Boolean);
    const updatedServerConfig: any = {};
    if (mcpEditorType === 'sse') {
      updatedServerConfig.type = 'sse';
      updatedServerConfig.url = mcpEditorUrl.trim();
    } else {
      updatedServerConfig.command = mcpEditorCommand.trim();
      if (argsArr.length > 0) updatedServerConfig.args = argsArr;
      if (Object.keys(envObj).length > 0) updatedServerConfig.env = envObj;
    }
    
    setTempConfig(prev => {
      if (!prev) return null;
      return {
        ...prev,
        mcp_servers: {
          ...prev.mcp_servers,
          [selectedMcpServer]: updatedServerConfig
        }
      };
    });
    
    showToast(`MCP server "${selectedMcpServer}" configuration staged!`, "success");
  };

  const testMcpConfig = async () => {
    if (!selectedMcpServer) return;
    setMcpTestStatus('testing');
    setMcpTestMessage('Testing configuration availability...');
    
    let envObj = {};
    if (mcpEditorEnv.trim()) {
      try {
        envObj = JSON.parse(mcpEditorEnv);
      } catch (e) {
        setMcpTestStatus('error');
        setMcpTestMessage('Invalid Environment JSON format.');
        showToast('Invalid Environment JSON format', 'error');
        return;
      }
    }
    
    try {
      const res = await fetch('/api/mcp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: selectedMcpServer,
          type: mcpEditorType,
          command: mcpEditorCommand,
          args: mcpEditorArgs.split('\n').map(a => a.trim()).filter(Boolean),
          env: envObj,
          url: mcpEditorUrl
        })
      });
      
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setMcpTestStatus(data.status);
      setMcpTestMessage(data.message);
      if (data.status === 'success') {
        showToast('MCP test passed successfully!', 'success');
      } else if (data.status === 'warning') {
        showToast('MCP test warning: command exists but failed run.', 'warning');
      } else {
        showToast('MCP test failed: connection or path error.', 'error');
      }
    } catch (err: any) {
      setMcpTestStatus('error');
      setMcpTestMessage(`Test error: ${err.message}`);
      showToast(`Test failed: ${err.message}`, 'error');
    }
  };

  return (
    <div className="flex h-[calc(100vh-180px)] border border-surface0 bg-mantle rounded-xl overflow-hidden shadow-lg">
      {/* Left pane - Server selector */}
      <aside className="w-[280px] border-r border-surface0 flex flex-col shrink-0 bg-mantle">
        <div className="p-4 border-b border-surface0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-overlay1 h-3.5 w-3.5" />
            <input 
              type="text"
              placeholder="Search servers..."
              value={mcpSearch}
              onChange={e => setMcpSearch(e.target.value)}
              className="w-full bg-crust border border-surface1 text-text text-xs rounded-lg pl-8 pr-3 py-2 outline-none focus:border-blue transition-all"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
          {filteredMcp.map(server => {
            const isDisabled = tempConfig.disabled_mcp.includes(server);
            const selected = selectedMcpServer === server;
            return (
              <div
                key={server}
                onClick={() => setSelectedMcpServer(server)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                  selected ? 'bg-surface0 text-blue font-semibold shadow-sm' : 'hover:bg-white/[0.02] text-subtext1'
                }`}
              >
                <div className="flex flex-col">
                  <span className="text-xs font-mono">{server}</span>
                  <span className="text-[9px] text-overlay1 mt-0.5">
                    {DEFAULT_SERVERS.has(server) ? 'Core Server' : 'Custom Server'}
                  </span>
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider scale-90 ${
                  isDisabled ? 'bg-red/10 text-red border border-red/20' : 'bg-green/10 text-green border border-green/20'
                }`}>
                  {isDisabled ? 'Off' : 'On'}
                </span>
              </div>
            );
          })}
        </div>

        <div className="p-3 border-t border-surface0">
          <button
            onClick={() => setShowAddMcpModal(true)}
            className="w-full py-2 bg-blue hover:bg-[#b0d2ff] text-crust text-xs font-bold font-display rounded-lg flex items-center justify-center gap-1.5 cursor-pointer transition-all duration-200"
          >
            <Plus className="h-4 w-4" /> Add Custom MCP
          </button>
        </div>
      </aside>

      {/* Right pane - Server Configuration Editor */}
      <div className="flex-1 overflow-y-auto bg-base p-8 flex flex-col gap-6">
        {selectedMcpServer ? (
          <div className="flex flex-col gap-5 max-w-[680px]">
            <div className="flex items-center justify-between border-b border-surface0 pb-4">
              <div>
                <h2 className="text-lg font-bold font-display text-blue font-mono">{selectedMcpServer}</h2>
                <p className="text-xs text-overlay2 mt-1">Configure parameters directly inside ~/.claude.json</p>
              </div>
              
              <div className="flex items-center gap-3">
                <span className="text-xs text-subtext1 font-semibold">Enable Server:</span>
                <Toggle 
                  checked={!tempConfig.disabled_mcp.includes(selectedMcpServer)}
                  onChange={() => handleMcpToggle(selectedMcpServer)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-4">
              {/* Connection Type */}
              <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                <label className="text-sm font-semibold text-subtext1">Connection Type:</label>
                <select
                  value={mcpEditorType}
                  onChange={e => setMcpEditorType(e.target.value as any)}
                  className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all"
                >
                  <option value="stdio">stdio (Command Line Process)</option>
                  <option value="sse">sse (HTTP Server-Sent Events)</option>
                </select>
              </div>

              {mcpEditorType === 'stdio' ? (
                <>
                  {/* Command */}
                  <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                    <label className="text-sm font-semibold text-subtext1 font-mono">command:</label>
                    <input 
                      type="text"
                      value={mcpEditorCommand}
                      onChange={e => setMcpEditorCommand(e.target.value)}
                      placeholder="npx"
                      className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono"
                    />
                  </div>

                  {/* Arguments */}
                  <div className="grid grid-cols-[160px_1fr] items-start gap-5">
                    <div className="flex flex-col">
                      <label className="text-sm font-semibold text-subtext1 font-mono">args:</label>
                      <span className="text-[10px] text-overlay1 mt-1">One parameter per line</span>
                    </div>
                    <textarea
                      rows={4}
                      value={mcpEditorArgs}
                      onChange={e => setMcpEditorArgs(e.target.value)}
                      placeholder="-y&#10;@modelcontextprotocol/server-postgres&#10;postgresql://localhost/postgres"
                      className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono resize-none"
                    />
                  </div>

                  {/* Environment variables */}
                  <div className="grid grid-cols-[160px_1fr] items-start gap-5">
                    <div className="flex flex-col">
                      <label className="text-sm font-semibold text-subtext1 font-mono">env:</label>
                      <span className="text-[10px] text-overlay1 mt-1">JSON dictionary format</span>
                    </div>
                    <textarea
                      rows={4}
                      value={mcpEditorEnv}
                      onChange={e => setMcpEditorEnv(e.target.value)}
                      placeholder='{&#10;  "PGPORT": "5432"&#10;}'
                      className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono resize-none"
                    />
                  </div>
                </>
              ) : (
                /* SSE URL */
                <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                  <label className="text-sm font-semibold text-subtext1 font-mono">url:</label>
                  <input 
                    type="text"
                    value={mcpEditorUrl}
                    onChange={e => setMcpEditorUrl(e.target.value)}
                    placeholder="https://mcp.context7.com/mcp"
                    className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono"
                  />
                </div>
              )}
            </div>

            {/* Testing status panel */}
            {mcpTestStatus !== 'idle' && (
              <div className={`p-3 rounded-lg flex items-start gap-2.5 text-xs border ${
                mcpTestStatus === 'testing' ? 'bg-blue/5 border-blue/20 text-blue' :
                mcpTestStatus === 'success' ? 'bg-green/5 border-green/20 text-green' :
                mcpTestStatus === 'warning' ? 'bg-peach/5 border-peach/20 text-peach' :
                'bg-red/5 border-red/20 text-red'
              }`}>
                <div className="shrink-0 mt-0.5">
                  {mcpTestStatus === 'testing' && <Sliders className="h-4 w-4 animate-spin" />}
                  {mcpTestStatus === 'success' && <CheckCircle2 className="h-4 w-4" />}
                  {mcpTestStatus === 'warning' && <AlertTriangle className="h-4 w-4" />}
                  {mcpTestStatus === 'error' && <XCircle className="h-4 w-4" />}
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="font-bold uppercase tracking-wider text-[9px]">
                    {mcpTestStatus === 'testing' && 'Running Diagnostics...'}
                    {mcpTestStatus === 'success' && 'Diagnostics Passed'}
                    {mcpTestStatus === 'warning' && 'Diagnostics Warning'}
                    {mcpTestStatus === 'error' && 'Diagnostics Failed'}
                  </span>
                  <span className="font-mono break-all leading-normal">{mcpTestMessage}</span>
                </div>
              </div>
            )}

            <div className="flex justify-between items-center border-t border-surface0 pt-6 mt-4">
              {!DEFAULT_SERVERS.has(selectedMcpServer) ? (
                <button
                  type="button"
                  onClick={() => deleteCustomMcp(selectedMcpServer)}
                  className="px-4 py-2 border border-red text-red hover:bg-red/5 text-xs font-bold font-display rounded-lg flex items-center gap-1.5 cursor-pointer transition-all"
                >
                  <TrashIcon className="h-4 w-4" /> Delete Custom Server
                </button>
              ) : <div />}

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={testMcpConfig}
                  disabled={mcpTestStatus === 'testing'}
                  className="px-4 py-2 border border-surface2 hover:border-blue text-text text-xs font-bold font-display rounded-lg flex items-center gap-1.5 cursor-pointer transition-all disabled:opacity-50"
                >
                  <Play className="h-4 w-4 text-blue" /> Test Configuration
                </button>

                <button
                  type="button"
                  onClick={saveMcpEditor}
                  className="px-5 py-2.5 bg-blue hover:bg-[#b0d2ff] text-crust text-xs font-bold font-display rounded-lg flex items-center gap-1.5 cursor-pointer shadow-md transition-all"
                >
                  <Save className="h-4 w-4" /> Save Server Configuration
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-overlay0">
            <Cpu className="h-12 w-12 text-surface2 mb-2" />
            <span>No MCP server selected. Add a custom server to get started.</span>
          </div>
        )}
      </div>
    </div>
  );
};
