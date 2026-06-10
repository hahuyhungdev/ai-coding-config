import React from 'react';
import { Cpu, X, Save, AlertTriangle } from 'lucide-react';

// --- Shared Modal Shell ---
const ModalShell: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}> = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null;
  return (
    <div
      className="fixed inset-0 bg-bg/80 backdrop-blur-md flex items-center justify-center z-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="glass-gold rounded-xl w-[520px] max-w-[90%] overflow-hidden flex flex-col shadow-2xl shadow-black/40 animate-fade-up"
        onClick={e => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
};

// --- ADD MCP MODAL ---
interface AddMcpModalProps {
  isOpen: boolean;
  onClose: () => void;
  newMcpName: string;
  setNewMcpName: (val: string) => void;
  newMcpType: 'stdio' | 'sse';
  setNewMcpType: (val: 'stdio' | 'sse') => void;
  newMcpCommand: string;
  setNewMcpCommand: (val: string) => void;
  newMcpArgs: string;
  setNewMcpArgs: (val: string) => void;
  newMcpEnv: string;
  setNewMcpEnv: (val: string) => void;
  newMcpUrl: string;
  setNewMcpUrl: (val: string) => void;
  onAdd: () => void;
}

export const AddMcpModal: React.FC<AddMcpModalProps> = ({
  isOpen, onClose,
  newMcpName, setNewMcpName,
  newMcpType, setNewMcpType,
  newMcpCommand, setNewMcpCommand,
  newMcpArgs, setNewMcpArgs,
  newMcpEnv, setNewMcpEnv,
  newMcpUrl, setNewMcpUrl,
  onAdd,
}) => {
  return (
    <ModalShell isOpen={isOpen} onClose={onClose}>
      <div className="p-5 border-b border-white/[0.08] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
            <Cpu className="h-4 w-4 text-accent" />
          </div>
          <h2 className="text-base font-display text-text-primary">Add MCP Server</h2>
        </div>
        <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors cursor-pointer">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="p-6 flex flex-col gap-4 overflow-y-auto max-h-[70vh]">
        {/* Server Name */}
        <div className="flex flex-col gap-1.5">
          <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Server Identifier</label>
          <input
            type="text"
            value={newMcpName}
            onChange={e => setNewMcpName(e.target.value)}
            placeholder="e.g. mysql-connector"
            className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300 font-mono placeholder:text-text-muted/40"
          />
        </div>

        {/* Server Type */}
        <div className="flex flex-col gap-1.5">
          <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Connection Protocol</label>
          <select
            value={newMcpType}
            onChange={e => setNewMcpType(e.target.value as 'stdio' | 'sse')}
            className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 transition-all duration-300"
          >
            <option value="stdio">stdio — Command Line</option>
            <option value="sse">sse — HTTP Server-Sent Events</option>
          </select>
        </div>

        {newMcpType === 'stdio' ? (
          <>
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Executable Command</label>
              <input
                type="text"
                value={newMcpCommand}
                onChange={e => setNewMcpCommand(e.target.value)}
                placeholder="e.g. npx"
                className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300 font-mono placeholder:text-text-muted/40"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between">
                <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Arguments</label>
                <span className="text-[10px] text-text-muted/70">One per line</span>
              </div>
              <textarea
                rows={3}
                value={newMcpArgs}
                onChange={e => setNewMcpArgs(e.target.value)}
                placeholder={"e.g.\n-y\n@modelcontextprotocol/server-postgres\npostgresql://localhost/postgres"}
                className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 transition-all duration-300 font-mono resize-none placeholder:text-text-muted/40"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between">
                <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Environment Variables (JSON)</label>
                <span className="text-[10px] text-text-muted/70">JSON format</span>
              </div>
              <textarea
                rows={3}
                value={newMcpEnv}
                onChange={e => setNewMcpEnv(e.target.value)}
                placeholder={'e.g. {\n  "PORT": "3306"\n}'}
                className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 transition-all duration-300 font-mono resize-none placeholder:text-text-muted/40"
              />
            </div>
          </>
        ) : (
          <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15] font-mono">URL</label>
            <input
              type="text"
              value={newMcpUrl}
              onChange={e => setNewMcpUrl(e.target.value)}
              placeholder="https://mcp.server.com/mcp"
              className="bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2.5 outline-none focus:border-accent/40 transition-all duration-300 font-mono placeholder:text-text-muted/40"
            />
          </div>
        )}
      </div>

      <div className="p-4 border-t border-white/[0.08] flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 border border-white/[0.10] hover:bg-white/[0.03] text-[12px] font-medium text-text-secondary rounded-lg cursor-pointer transition-all duration-300"
        >
          Cancel
        </button>
        <button
          onClick={onAdd}
          className="px-5 py-2.5 bg-accent/90 hover:bg-accent text-bg text-[12px] font-semibold rounded-lg cursor-pointer shadow-[0_0_15px_rgba(201,165,92,0.15)] transition-all duration-300"
        >
          Add Server
        </button>
      </div>
    </ModalShell>
  );
};

// --- APPLY CHANGES MODAL ---
interface ApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (force: boolean) => void;
}

export const ApplyModal: React.FC<ApplyModalProps> = ({ isOpen, onClose, onApply }) => {
  return (
    <ModalShell isOpen={isOpen} onClose={onClose}>
      <div className="p-5 border-b border-white/[0.08] flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-success/10 border border-success/20 flex items-center justify-center">
          <Save className="h-4 w-4 text-success" />
        </div>
        <h2 className="text-base font-display text-text-primary">Apply Staged Changes?</h2>
      </div>
      <div className="p-6 text-[13px] text-text-secondary leading-relaxed flex flex-col gap-3">
        <p>This will write configuration settings to the repository templates and invoke the global installation script to sync CLI files.</p>
        <p>Choose <strong className="text-text-primary">Standard Apply</strong> for standard config mapping, or <strong className="text-warning">Force Overwrite</strong> to overwrite all destination files completely.</p>
      </div>
      <div className="p-4 border-t border-white/[0.08] flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 border border-white/[0.10] hover:bg-white/[0.03] text-[12px] font-medium text-text-secondary rounded-lg cursor-pointer transition-all duration-300"
        >
          Cancel
        </button>
        <button
          onClick={() => onApply(true)}
          className="px-4 py-2 bg-warning/10 border border-warning/20 hover:bg-warning/20 text-warning text-[12px] font-semibold rounded-lg cursor-pointer transition-all duration-300"
        >
          Force Overwrite
        </button>
        <button
          onClick={() => onApply(false)}
          className="px-4 py-2 bg-success/90 hover:bg-success text-bg text-[12px] font-semibold rounded-lg cursor-pointer shadow-[0_0_15px_rgba(52,211,153,0.15)] transition-all duration-300"
        >
          Standard Apply
        </button>
      </div>
    </ModalShell>
  );
};

// --- DISCARD CHANGES MODAL ---
interface DiscardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDiscard: () => void;
}

export const DiscardModal: React.FC<DiscardModalProps> = ({ isOpen, onClose, onDiscard }) => {
  return (
    <ModalShell isOpen={isOpen} onClose={onClose}>
      <div className="p-5 border-b border-white/[0.08] flex items-center gap-3">
        <div className="h-8 w-8 rounded-lg bg-error/10 border border-error/20 flex items-center justify-center">
          <AlertTriangle className="h-4 w-4 text-error" />
        </div>
        <h2 className="text-base font-display text-text-primary">Discard Changes?</h2>
      </div>
      <div className="p-6 text-[13px] text-text-secondary leading-relaxed">
        <p>Are you sure you want to discard all staged configuration changes? All modified fields will revert to their original saved values immediately.</p>
      </div>
      <div className="p-4 border-t border-white/[0.08] flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 border border-white/[0.10] hover:bg-white/[0.03] text-[12px] font-medium text-text-secondary rounded-lg cursor-pointer transition-all duration-300"
        >
          Cancel
        </button>
        <button
          onClick={onDiscard}
          className="px-4 py-2 bg-error/10 border border-error/20 hover:bg-error/20 text-error text-[12px] font-semibold rounded-lg cursor-pointer transition-all duration-300"
        >
          Discard Changes
        </button>
      </div>
    </ModalShell>
  );
};
