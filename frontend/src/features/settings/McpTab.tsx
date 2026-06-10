import React, { useState, useEffect } from 'react';
import type { FullConfig } from '../../types';
import { Toggle } from '../../components/Toggle';
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
  const [mcpEditorType, setMcpEditorType] = useState<'stdio' | 'sse'>('stdio');
  const [mcpEditorCommand, setMcpEditorCommand] = useState<string>('');
  const [mcpEditorArgs, setMcpEditorArgs] = useState<string>('');
  const [mcpEditorUrl, setMcpEditorUrl] = useState<string>('');
  const [mcpEditorEnv, setMcpEditorEnv] = useState<string>('');
  const [mcpTestStatus, setMcpTestStatus] = useState<'idle' | 'testing' | 'success' | 'error' | 'warning'>('idle');
  const [mcpTestMessage, setMcpTestMessage] = useState<string>('');

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
      try { envObj = JSON.parse(mcpEditorEnv); }
      catch { showToast("Invalid Environment JSON. Please verify syntax.", "error"); return; }
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
      return { ...prev, mcp_servers: { ...prev.mcp_servers, [selectedMcpServer]: updatedServerConfig } };
    });
    showToast(`MCP server "${selectedMcpServer}" configuration staged!`, "success");
  };

  const testMcpConfig = async () => {
    if (!selectedMcpServer) return;
    setMcpTestStatus('testing');
    setMcpTestMessage('Testing configuration availability...');
    let envObj = {};
    if (mcpEditorEnv.trim()) {
      try { envObj = JSON.parse(mcpEditorEnv); }
      catch { setMcpTestStatus('error'); setMcpTestMessage('Invalid Environment JSON format.'); return; }
    }
    try {
      const res = await fetch('/api/mcp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedMcpServer, type: mcpEditorType, command: mcpEditorCommand, args: mcpEditorArgs.split('\n').map(a => a.trim()).filter(Boolean), env: envObj, url: mcpEditorUrl })
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setMcpTestStatus(data.status);
      setMcpTestMessage(data.message);
      if (data.status === 'success') showToast('MCP test passed!', 'success');
      else if (data.status === 'warning') showToast('MCP test warning: command exists but failed run.', 'warning');
      else showToast('MCP test failed.', 'error');
    } catch (err: any) {
      setMcpTestStatus('error');
      setMcpTestMessage(`Test error: ${err.message}`);
      showToast(`Test failed: ${err.message}`, 'error');
    }
  };

  const inputBase = "bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300";

  return (
    <div className="flex h-[calc(100vh-180px)] glass rounded-xl overflow-hidden">
      {/* Left pane — Server selector */}
      <aside className="w-[280px] border-r border-white/[0.08] flex flex-col shrink-0 bg-white/[0.03]">
        <div className="p-4 border-b border-white/[0.08]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-3.5 w-3.5" />
            <input
              type="text"
              placeholder="Search servers..."
              value={mcpSearch}
              onChange={e => setMcpSearch(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-xs rounded-lg pl-8 pr-3 py-2 outline-none focus:border-accent/40 transition-all duration-300"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-0.5">
          {filteredMcp.map(server => {
            const isDisabled = tempConfig.disabled_mcp.includes(server);
            const selected = selectedMcpServer === server;
            return (
              <div
                key={server}
                onClick={() => setSelectedMcpServer(server)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                  selected
                    ? 'bg-accent/[0.08] border border-accent/15 text-accent'
                    : 'hover:bg-white/[0.04] text-text-secondary border border-transparent'
                }`}
              >
                <div className="flex flex-col">
                  <span className="text-xs font-mono">{server}</span>
                  <span className="text-[9px] text-text-muted mt-0.5">
                    {DEFAULT_SERVERS.has(server) ? 'Core' : 'Custom'}
                  </span>
                </div>
                <span className={`text-[9px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                  isDisabled ? 'bg-error/10 text-error border border-error/15' : 'bg-success/10 text-success border border-success/15'
                }`}>
                  {isDisabled ? 'Off' : 'On'}
                </span>
              </div>
            );
          })}
        </div>

        <div className="p-3 border-t border-white/[0.08]">
          <button
            onClick={() => setShowAddMcpModal(true)}
            className="w-full py-2 bg-accent/90 hover:bg-accent text-bg text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 cursor-pointer transition-all duration-300"
          >
            <Plus className="h-4 w-4" /> Add Custom MCP
          </button>
        </div>
      </aside>

      {/* Right pane — Editor */}
      <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-6">
        {selectedMcpServer ? (
          <div className="flex flex-col gap-5 max-w-[680px] animate-fade-up">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div>
                <h2 className="text-lg font-display text-accent font-mono">{selectedMcpServer}</h2>
                <p className="text-xs text-text-muted mt-1">Configure parameters for ~/.claude.json</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-secondary font-medium">Enable:</span>
                <Toggle checked={!tempConfig.disabled_mcp.includes(selectedMcpServer)} onChange={() => handleMcpToggle(selectedMcpServer)} />
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                <label className="text-sm font-medium text-text-secondary">Connection Type:</label>
                <select value={mcpEditorType} onChange={e => setMcpEditorType(e.target.value as any)} className={inputBase}>
                  <option value="stdio">stdio — Command Line</option>
                  <option value="sse">sse — HTTP Server-Sent Events</option>
                </select>
              </div>

              {mcpEditorType === 'stdio' ? (
                <>
                  <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                    <label className="text-sm font-medium text-text-secondary font-mono">command:</label>
                    <input type="text" value={mcpEditorCommand} onChange={e => setMcpEditorCommand(e.target.value)} placeholder="npx" className={`${inputBase} font-mono`} />
                  </div>
                  <div className="grid grid-cols-[160px_1fr] items-start gap-5">
                    <div>
                      <label className="text-sm font-medium text-text-secondary font-mono">args:</label>
                      <span className="text-[10px] text-text-muted block mt-1">One per line</span>
                    </div>
                    <textarea rows={4} value={mcpEditorArgs} onChange={e => setMcpEditorArgs(e.target.value)} placeholder="-y\n@modelcontextprotocol/server-postgres\npostgresql://localhost/postgres" className={`${inputBase} font-mono resize-none`} />
                  </div>
                  <div className="grid grid-cols-[160px_1fr] items-start gap-5">
                    <div>
                      <label className="text-sm font-medium text-text-secondary font-mono">env:</label>
                      <span className="text-[10px] text-text-muted block mt-1">JSON format</span>
                    </div>
                    <textarea rows={4} value={mcpEditorEnv} onChange={e => setMcpEditorEnv(e.target.value)} placeholder={'{\n  "PGPORT": "5432"\n}'} className={`${inputBase} font-mono resize-none`} />
                  </div>
                </>
              ) : (
                <div className="grid grid-cols-[160px_1fr] items-center gap-5">
                  <label className="text-sm font-medium text-text-secondary font-mono">url:</label>
                  <input type="text" value={mcpEditorUrl} onChange={e => setMcpEditorUrl(e.target.value)} placeholder="https://mcp.context7.com/mcp" className={`${inputBase} font-mono`} />
                </div>
              )}
            </div>

            {/* Test status */}
            {mcpTestStatus !== 'idle' && (
              <div className={`p-3 rounded-lg flex items-start gap-2.5 text-xs border ${
                mcpTestStatus === 'testing' ? 'bg-info/[0.06] border-info/15 text-info' :
                mcpTestStatus === 'success' ? 'bg-success/[0.06] border-success/15 text-success' :
                mcpTestStatus === 'warning' ? 'bg-warning/[0.06] border-warning/15 text-warning' :
                'bg-error/[0.06] border-error/15 text-error'
              }`}>
                <div className="shrink-0 mt-0.5">
                  {mcpTestStatus === 'testing' && <Sliders className="h-4 w-4 animate-spin" />}
                  {mcpTestStatus === 'success' && <CheckCircle2 className="h-4 w-4" />}
                  {mcpTestStatus === 'warning' && <AlertTriangle className="h-4 w-4" />}
                  {mcpTestStatus === 'error' && <XCircle className="h-4 w-4" />}
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold uppercase tracking-wider text-[9px]">
                    {mcpTestStatus === 'testing' && 'Running Diagnostics...'}
                    {mcpTestStatus === 'success' && 'Diagnostics Passed'}
                    {mcpTestStatus === 'warning' && 'Diagnostics Warning'}
                    {mcpTestStatus === 'error' && 'Diagnostics Failed'}
                  </span>
                  <span className="font-mono break-all leading-normal">{mcpTestMessage}</span>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-between items-center border-t border-white/[0.08] pt-6 mt-4">
              {!DEFAULT_SERVERS.has(selectedMcpServer) ? (
                <button type="button" onClick={() => deleteCustomMcp(selectedMcpServer)} className="px-4 py-2 border border-error/20 text-error hover:bg-error/[0.04] text-xs font-medium rounded-lg flex items-center gap-1.5 cursor-pointer transition-all duration-300">
                  <TrashIcon className="h-4 w-4" /> Delete Server
                </button>
              ) : <div />}

              <div className="flex gap-3">
                <button type="button" onClick={testMcpConfig} disabled={mcpTestStatus === 'testing'} className="px-4 py-2 border border-white/[0.10] hover:border-accent/30 text-text-secondary text-xs font-medium rounded-lg flex items-center gap-1.5 cursor-pointer transition-all duration-300 disabled:opacity-40">
                  <Play className="h-4 w-4 text-accent" /> Test
                </button>
                <button type="button" onClick={saveMcpEditor} className="px-5 py-2.5 bg-accent/90 hover:bg-accent text-bg text-xs font-semibold rounded-lg flex items-center gap-1.5 cursor-pointer shadow-[0_0_15px_rgba(201,165,92,0.12)] transition-all duration-300">
                  <Save className="h-4 w-4" /> Save
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-text-muted">
            <Cpu className="h-12 w-12 opacity-20 mb-3" />
            <span className="text-sm">Select a server to configure</span>
          </div>
        )}
      </div>
    </div>
  );
};
