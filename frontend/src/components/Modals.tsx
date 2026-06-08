import React from 'react';
import { Cpu, X, Save, AlertTriangle } from 'lucide-react';

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
  isOpen,
  onClose,
  newMcpName,
  setNewMcpName,
  newMcpType,
  setNewMcpType,
  newMcpCommand,
  setNewMcpCommand,
  newMcpArgs,
  setNewMcpArgs,
  newMcpEnv,
  setNewMcpEnv,
  newMcpUrl,
  setNewMcpUrl,
  onAdd,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-crust/70 backdrop-blur-sm flex items-center justify-center z-50 transition-opacity duration-200">
      <div className="bg-mantle border-2 border-blue shadow-2xl rounded-xl w-[520px] max-w-[90%] overflow-hidden flex flex-col transform scale-100 transition-all">
        <div className="p-5 border-b border-surface0 flex items-center justify-between border-l-4 border-l-blue">
          <div className="flex items-center gap-2.5">
            <Cpu className="h-5 w-5 text-blue" />
            <h2 className="text-base font-bold font-display">Add Custom MCP Server</h2>
          </div>
          <button 
            onClick={onClose}
            className="text-overlay1 hover:text-text cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <div className="p-6 flex flex-col gap-4 overflow-y-auto max-h-[70vh]">
          {/* Server Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-overlay2 uppercase tracking-wide">Server Identifier:</label>
            <input 
              type="text"
              value={newMcpName}
              onChange={e => setNewMcpName(e.target.value)}
              placeholder="e.g. mysql-connector"
              className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono"
            />
          </div>

          {/* Server Type */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-bold text-overlay2 uppercase tracking-wide">Connection Protocol:</label>
            <select
              value={newMcpType}
              onChange={e => setNewMcpType(e.target.value as 'stdio' | 'sse')}
              className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all"
            >
              <option value="stdio">stdio (Command Line execution)</option>
              <option value="sse">sse (HTTP Server-Sent Events)</option>
            </select>
          </div>

          {newMcpType === 'stdio' ? (
            <>
              {/* Command */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-overlay2 uppercase tracking-wide">Executable Command:</label>
                <input 
                  type="text"
                  value={newMcpCommand}
                  onChange={e => setNewMcpCommand(e.target.value)}
                  placeholder="e.g. npx"
                  className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono"
                />
              </div>

              {/* Arguments */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between">
                  <label className="text-xs font-bold text-overlay2 uppercase tracking-wide">Arguments:</label>
                  <span className="text-[10px] text-overlay1">One parameter per line</span>
                </div>
                <textarea 
                  rows={3}
                  value={newMcpArgs}
                  onChange={e => setNewMcpArgs(e.target.value)}
                  placeholder="e.g.&#10;-y&#10;@modelcontextprotocol/server-postgres&#10;postgresql://localhost/postgres"
                  className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono resize-none"
                />
              </div>

              {/* Env variables */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between">
                  <label className="text-xs font-bold text-overlay2 uppercase tracking-wide">Environment Variables (JSON):</label>
                  <span className="text-[10px] text-overlay1">JSON Dictionary Format</span>
                </div>
                <textarea 
                  rows={3}
                  value={newMcpEnv}
                  onChange={e => setNewMcpEnv(e.target.value)}
                  placeholder='e.g. {&#10;  "PORT": "3306"&#10;}'
                  className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono resize-none"
                />
              </div>
            </>
          ) : (
            /* SSE URL */
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-overlay2 uppercase tracking-wide font-mono">url:</label>
              <input 
                type="text"
                value={newMcpUrl}
                onChange={e => setNewMcpUrl(e.target.value)}
                placeholder="https://mcp.server.com/mcp"
                className="bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue transition-all font-mono"
              />
            </div>
          )}
        </div>

        <div className="p-4 bg-crust border-t border-surface0 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-surface2 hover:bg-white/5 text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Cancel
          </button>
          <button 
            onClick={onAdd}
            className="px-5 py-2.5 bg-blue text-crust hover:bg-[#b0d2ff] text-xs font-bold font-display rounded-lg cursor-pointer shadow-md transition-all"
          >
            Add Server to Staging
          </button>
        </div>
      </div>
    </div>
  );
};

// --- APPLY CHANGES MODAL ---
interface ApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (force: boolean) => void;
}

export const ApplyModal: React.FC<ApplyModalProps> = ({
  isOpen,
  onClose,
  onApply,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-crust/70 backdrop-blur-sm flex items-center justify-center z-45 transition-opacity duration-200">
      <div className="bg-mantle border-2 border-blue shadow-2xl rounded-xl w-[500px] max-w-[90%] overflow-hidden flex flex-col transform scale-100 transition-all">
        <div className="p-5 border-b border-surface0 flex items-center gap-3 border-l-4 border-l-green">
          <Save className="h-5 w-5 text-green" />
          <h2 className="text-base font-bold font-display">Apply Staged Changes?</h2>
        </div>
        <div className="p-6 text-sm text-subtext1 leading-relaxed flex flex-col gap-3">
          <p>This will write configuration settings to the repository templates and invoke the global installation script to sync CLI files.</p>
          <p>Choose <strong>Standard Apply</strong> for standard config mapping, or <strong>Force Overwrite</strong> to overwrite all destination files completely without checks.</p>
        </div>
        <div className="p-4 bg-crust border-t border-surface0 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-surface2 hover:bg-white/5 text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Cancel
          </button>
          <button 
            onClick={() => onApply(true)}
            className="px-4 py-2 bg-peach text-crust hover:bg-[#f7b795] text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Force Overwrite
          </button>
          <button 
            onClick={() => onApply(false)}
            className="px-4 py-2 bg-green text-crust hover:bg-[#b3e3a3] text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Standard Apply
          </button>
        </div>
      </div>
    </div>
  );
};

// --- DISCARD CHANGES MODAL ---
interface DiscardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDiscard: () => void;
}

export const DiscardModal: React.FC<DiscardModalProps> = ({
  isOpen,
  onClose,
  onDiscard,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-crust/70 backdrop-blur-sm flex items-center justify-center z-45 transition-opacity duration-200">
      <div className="bg-mantle border-2 border-red shadow-2xl rounded-xl w-[500px] max-w-[90%] overflow-hidden flex flex-col transform scale-100 transition-all">
        <div className="p-5 border-b border-surface0 flex items-center gap-3 border-l-4 border-l-red">
          <AlertTriangle className="h-5 w-5 text-red" />
          <h2 className="text-base font-bold font-display">Discard Staged Changes?</h2>
        </div>
        <div className="p-6 text-sm text-subtext1 leading-relaxed">
          <p>Are you sure you want to discard all staged configuration changes? All modified fields will revert to their original saved values immediately.</p>
        </div>
        <div className="p-4 bg-crust border-t border-surface0 flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-surface2 hover:bg-white/5 text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Cancel
          </button>
          <button 
            onClick={onDiscard}
            className="px-4 py-2 bg-red text-crust hover:bg-[#ee99a0] text-xs font-bold font-display rounded-lg cursor-pointer transition-all"
          >
            Discard Changes
          </button>
        </div>
      </div>
    </div>
  );
};
