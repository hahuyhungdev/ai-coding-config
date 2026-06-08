import React from 'react';
import type { FullConfig } from '../types';
import { Toggle } from './Toggle';
import { 
  Sliders, Search, CheckCircle2, XCircle, GitBranch, 
  Save, Trash2, MessageSquareCode, Terminal as TerminalIcon, 
  Sparkles, Cpu
} from 'lucide-react';

interface SidebarProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  handleTargetToggle: (cid: string) => void;
  handleMcpToggle: (server: string) => void;
  batchMcp: (enable: boolean) => void;
  mcpSearch: string;
  setMcpSearch: (val: string) => void;
  filteredMcp: string[];
  hasPendingChanges: boolean;
  pendingChanges: Array<{ key: string; text: string; type: 'add' | 'del' | 'mod' }>;
  setShowApplyModal: (show: boolean) => void;
  setShowDiscardModal: (show: boolean) => void;
}

const CLI_CONFIGS: Record<string, { name: string; icon: string }> = {
  claude: { name: "Claude Code", icon: "message-square-code" },
  codex: { name: "Codex CLI", icon: "terminal" },
  agy: { name: "Antigravity", icon: "sparkles" }
};

export const Sidebar: React.FC<SidebarProps> = ({
  initialConfig,
  tempConfig,
  handleTargetToggle,
  handleMcpToggle,
  batchMcp,
  mcpSearch,
  setMcpSearch,
  filteredMcp,
  hasPendingChanges,
  pendingChanges,
  setShowApplyModal,
  setShowDiscardModal
}) => {
  return (
    <aside className="w-[340px] bg-mantle border-r border-surface0 flex flex-col h-full shrink-0">
      <div className="p-6 border-b border-surface0 flex flex-col gap-1">
        <h1 className="text-xl font-extrabold bg-gradient-to-r from-blue to-mauve bg-clip-text text-transparent font-display flex items-center gap-2">
          <Sliders className="h-5 w-5 text-blue shrink-0" /> Config Engine
        </h1>
        <p className="text-[10px] text-overlay2 font-bold tracking-wider uppercase">Vite React TS Dashboard</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-6">
        {/* Targets */}
        <div>
          <div className="section-title text-xs font-bold font-display text-overlay1 tracking-wider uppercase mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-overlay1" /> CLI Targets
          </div>
          <div className="flex flex-col gap-2">
            {Object.entries(CLI_CONFIGS).map(([cid, info]) => {
              const checked = tempConfig.targets[cid];
              const modified = initialConfig.targets[cid] !== checked;
              return (
                <div 
                  key={cid} 
                  onClick={() => handleTargetToggle(cid)}
                  className={`flex items-center justify-between p-3 bg-surface0 border rounded-lg cursor-pointer transition-all duration-200 ${
                    modified ? 'border-peach shadow-sm shadow-peach/10' : 'border-surface1 hover:border-surface2'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {cid === 'claude' && <MessageSquareCode className="h-4 w-4 text-blue" />}
                    {cid === 'codex' && <TerminalIcon className="h-4 w-4 text-mauve" />}
                    {cid === 'agy' && <Sparkles className="h-4 w-4 text-peach" />}
                    <div>
                      <div className="text-sm font-semibold font-display">{info.name}</div>
                      <div className="text-[10px] text-overlay2">
                        {checked ? 'Enabled in install' : 'Excluded from install'}
                      </div>
                    </div>
                  </div>
                  <div onClick={e => e.stopPropagation()}>
                    <Toggle checked={checked} onChange={() => handleTargetToggle(cid)} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Quick MCP Toggles */}
        <div>
          <div className="section-title text-xs font-bold font-display text-overlay1 tracking-wider uppercase mb-3 flex items-center gap-2">
            <Cpu className="h-4 w-4 text-overlay1" /> MCP Quick Toggle
          </div>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-overlay1 h-3.5 w-3.5" />
            <input 
              type="text" 
              placeholder="Search MCP servers..."
              value={mcpSearch}
              onChange={e => setMcpSearch(e.target.value)}
              className="w-full bg-crust border border-surface1 text-text text-xs rounded-lg pl-9 pr-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all duration-200"
            />
          </div>
          
          <div className="grid grid-cols-2 gap-2 mb-3">
            <button 
              onClick={() => batchMcp(true)}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-surface0 border border-surface1 hover:border-green hover:text-green text-[11px] font-bold rounded-md transition-all duration-200 cursor-pointer"
            >
              <CheckCircle2 className="h-3 w-3" /> All On
            </button>
            <button 
              onClick={() => batchMcp(false)}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-surface0 border border-surface1 hover:border-red hover:text-red text-[11px] font-bold rounded-md transition-all duration-200 cursor-pointer"
            >
              <XCircle className="h-3 w-3" /> All Off
            </button>
          </div>

          <div className="max-h-[160px] overflow-y-auto border border-surface0 rounded-lg bg-crust">
            {filteredMcp.length > 0 ? (
              filteredMcp.map(server => {
                const isInitDisabled = initialConfig.disabled_mcp.includes(server);
                const isInitEnabled = server in initialConfig.mcp_servers && !isInitDisabled;
                const isTempDisabled = tempConfig.disabled_mcp.includes(server);
                const isTempEnabled = server in tempConfig.mcp_servers && !isTempDisabled;
                const modified = isInitEnabled !== isTempEnabled;
                
                return (
                  <div 
                    key={server}
                    className={`flex items-center justify-between px-3 py-2 border-b border-surface0/50 last:border-b-0 hover:bg-white/[0.01] transition-all duration-200 ${
                      modified ? 'border-l-2 border-l-peach bg-peach/[0.02]' : ''
                    }`}
                  >
                    <span className="text-xs font-mono text-subtext1">{server}</span>
                    <Toggle checked={isTempEnabled} onChange={() => handleMcpToggle(server)} />
                  </div>
                );
              })
            ) : (
              <div className="text-center text-xs text-overlay0 py-4">No servers found</div>
            )}
          </div>
        </div>

        {/* Staged changes */}
        <div>
          <div className="section-title text-xs font-bold font-display text-overlay1 tracking-wider uppercase mb-3 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-overlay1" /> Staged Changes
          </div>
          <div className={`bg-crust border rounded-lg p-3 min-h-[80px] max-h-[160px] overflow-y-auto flex flex-col gap-1.5 transition-all duration-200 ${
            hasPendingChanges ? 'border-peach/50 ring-1 ring-peach/10' : 'border-surface1 border-dashed'
          }`}>
            {hasPendingChanges ? (
              pendingChanges.map(change => (
                <div 
                  key={change.key} 
                  className={`text-[11px] font-mono p-1 px-2 rounded-md ${
                    change.type === 'add' ? 'text-green bg-green/5' : 
                    change.type === 'del' ? 'text-red bg-red/5' : 'text-peach bg-peach/5'
                  }`}
                >
                  • {change.text}
                </div>
              ))
            ) : (
              <div className="m-auto text-xs text-overlay0 text-center">No pending changes.</div>
            )}
          </div>
        </div>
      </div>

      {/* Footer actions */}
      <div className="p-5 border-t border-surface0 bg-crust flex flex-col gap-2">
        <button 
          disabled={!hasPendingChanges}
          onClick={() => setShowApplyModal(true)}
          className="btn-primary w-full py-2.5 bg-green hover:bg-[#b3e3a3] disabled:opacity-30 disabled:cursor-not-allowed disabled:transform-none text-crust font-display font-bold text-sm rounded-lg flex items-center justify-center gap-2 shadow-md hover:shadow-green/20 cursor-pointer transition-all duration-200"
        >
          <Save className="h-4 w-4" /> Apply Changes
        </button>
        <button 
          disabled={!hasPendingChanges}
          onClick={() => setShowDiscardModal(true)}
          className="w-full py-2.5 bg-transparent border border-red hover:bg-red/5 disabled:opacity-30 disabled:cursor-not-allowed text-red font-display font-bold text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-all duration-200"
        >
          <Trash2 className="h-4 w-4" /> Discard Changes
        </button>
      </div>
    </aside>
  );
};
