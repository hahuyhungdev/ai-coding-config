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
    <aside className="w-[320px] bg-surface/60 backdrop-blur-xl border-r border-white/[0.08] flex flex-col h-full shrink-0 animate-slide-left">
      {/* Brand */}
      <div className="p-6 border-b border-white/[0.08]">
        <div className="flex items-center gap-3 mb-1.5">
          <div className="h-8 w-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Sliders className="h-4 w-4 text-accent" />
          </div>
          <div>
            <h1 className="text-lg font-display text-gold-shimmer leading-tight">
              Config Engine
            </h1>
            <p className="text-[10px] text-text-muted font-medium tracking-widest uppercase mt-0.5">
              AI Coding Dashboard
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-6">
        {/* Targets */}
        <section className="animate-fade-up stagger-1">
          <div className="text-[10px] font-semibold text-text-muted tracking-[0.15] uppercase mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 text-accent/50" /> CLI Targets
          </div>
          <div className="flex flex-col gap-1.5">
            {Object.entries(CLI_CONFIGS).map(([cid, info]) => {
              const checked = tempConfig.targets[cid];
              const modified = initialConfig.targets[cid] !== checked;
              return (
                <div
                  key={cid}
                  onClick={() => handleTargetToggle(cid)}
                  className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all duration-300 ${
                    modified
                      ? 'bg-warning/[0.06] border border-warning/20'
                      : 'bg-white/[0.04] border border-transparent hover:bg-white/[0.04] hover:border-white/[0.10]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {cid === 'claude' && <MessageSquareCode className="h-4 w-4 text-[#60a5fa]" />}
                    {cid === 'codex' && <TerminalIcon className="h-4 w-4 text-[#50fa7b]" />}
                    {cid === 'agy' && <Sparkles className="h-4 w-4 text-[#f59e0b]" />}
                    <div>
                      <div className="text-[13px] font-medium text-text-primary">{info.name}</div>
                      <div className="text-[10px] text-text-muted">
                        {checked ? 'Enabled' : 'Excluded'}
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
        </section>

        {/* Divider */}
        <div className="divider-gold" />

        {/* Quick MCP Toggles */}
        <section className="animate-fade-up stagger-2">
          <div className="text-[10px] font-semibold text-text-muted tracking-[0.15] uppercase mb-3 flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-accent/50" /> MCP Quick Toggle
          </div>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-3.5 w-3.5" />
            <input
              type="text"
              placeholder="Search servers..."
              value={mcpSearch}
              onChange={e => setMcpSearch(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-xs rounded-lg pl-9 pr-3 py-2.5 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300 placeholder:text-text-muted/70"
            />
          </div>

          <div className="grid grid-cols-2 gap-1.5 mb-3">
            <button
              onClick={() => batchMcp(true)}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-success/[0.06] border border-success/15 hover:border-success/30 hover:bg-success/[0.1] text-success text-[11px] font-medium rounded-md transition-all duration-300 cursor-pointer"
            >
              <CheckCircle2 className="h-3 w-3" /> All On
            </button>
            <button
              onClick={() => batchMcp(false)}
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-error/[0.06] border border-error/15 hover:border-error/30 hover:bg-error/[0.1] text-error text-[11px] font-medium rounded-md transition-all duration-300 cursor-pointer"
            >
              <XCircle className="h-3 w-3" /> All Off
            </button>
          </div>

          <div className="max-h-[160px] overflow-y-auto rounded-lg border border-white/[0.08] bg-white/[0.03]">
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
                    className={`flex items-center justify-between px-3 py-2 border-b border-white/[0.05] last:border-b-0 transition-all duration-200 ${
                      modified
                        ? 'border-l-2 border-l-warning bg-warning/[0.03]'
                        : 'hover:bg-white/[0.04]'
                    }`}
                  >
                    <span className="text-[11px] font-mono text-text-secondary">{server}</span>
                    <Toggle checked={isTempEnabled} onChange={() => handleMcpToggle(server)} />
                  </div>
                );
              })
            ) : (
              <div className="text-center text-[11px] text-text-muted py-4">No servers found</div>
            )}
          </div>
        </section>

        {/* Divider */}
        <div className="divider-gold" />

        {/* Staged changes */}
        <section className="animate-fade-up stagger-3">
          <div className="text-[10px] font-semibold text-text-muted tracking-[0.15] uppercase mb-3 flex items-center gap-2">
            <GitBranch className="h-3.5 w-3.5 text-accent/50" /> Staged Changes
          </div>
          <div className={`rounded-lg p-3 min-h-[80px] max-h-[160px] overflow-y-auto flex flex-col gap-1.5 transition-all duration-300 ${
            hasPendingChanges
              ? 'bg-accent/[0.03] border border-accent/15'
              : 'bg-white/[0.03] border border-dashed border-white/[0.10]'
          }`}>
            {hasPendingChanges ? (
              pendingChanges.map(change => (
                <div
                  key={change.key}
                  className={`text-[11px] font-mono p-1.5 px-2.5 rounded-md ${
                    change.type === 'add' ? 'text-success bg-success/[0.06]' :
                    change.type === 'del' ? 'text-error bg-error/[0.06]' : 'text-warning bg-warning/[0.06]'
                  }`}
                >
                  • {change.text}
                </div>
              ))
            ) : (
              <div className="m-auto text-[11px] text-text-muted text-center">No pending changes</div>
            )}
          </div>
        </section>
      </div>

      {/* Footer actions */}
      <div className="p-5 border-t border-white/[0.08] bg-bg/50 flex flex-col gap-2">
        <button
          disabled={!hasPendingChanges}
          onClick={() => setShowApplyModal(true)}
          className="w-full py-2.5 bg-accent/90 hover:bg-accent disabled:opacity-20 disabled:cursor-not-allowed text-bg font-semibold text-sm rounded-lg flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(201,165,92,0.15)] hover:shadow-[0_0_30px_rgba(201,165,92,0.25)] cursor-pointer transition-all duration-300"
        >
          <Save className="h-4 w-4" /> Apply Changes
        </button>
        <button
          disabled={!hasPendingChanges}
          onClick={() => setShowDiscardModal(true)}
          className="w-full py-2.5 bg-transparent border border-white/[0.10] hover:border-error/30 hover:bg-error/[0.04] disabled:opacity-20 disabled:cursor-not-allowed text-text-secondary hover:text-error font-medium text-sm rounded-lg flex items-center justify-center gap-2 cursor-pointer transition-all duration-300"
        >
          <Trash2 className="h-4 w-4" /> Discard
        </button>
      </div>
    </aside>
  );
};
