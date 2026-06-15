import React from 'react';
import type { FullConfig } from '../../types';
import { Toggle } from '../../components/Toggle';
import { Sliders, ShieldCheck, FileText, X } from 'lucide-react';

interface ClaudeTabProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  handleClaudeEnvChange: (key: string, value: string) => void;
  handleClaudePermsChange: (key: string, value: string) => void;
}

export const ClaudeTab: React.FC<ClaudeTabProps> = ({
  initialConfig,
  tempConfig,
  setTempConfig,
  handleClaudeEnvChange,
  handleClaudePermsChange
}) => {
  const [showInstructions, setShowInstructions] = React.useState(false);
  const isInstructionsModified = initialConfig.claude_instructions !== tempConfig.claude_instructions;

  const inputBase = "w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300";
  const labelBase = "text-sm font-medium text-text-secondary";

  return (
    <div className="flex flex-col gap-5 w-full">
      <div>
        <h2 className="font-display text-2xl text-text-primary mb-1">Claude Code</h2>
        <p className="text-sm text-text-muted">Configure LLM environment and permission policies</p>
      </div>

      <div className="flex flex-col gap-5">
        {/* Card 1: LLM & Environment */}
        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-1">
          <div className="text-[13px] font-semibold text-[#60a5fa] border-b border-white/[0.08] pb-3 flex items-center gap-2">
            <Sliders className="h-4 w-4" /> LLM & Environment Configuration
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="max-thinking-tokens" className={labelBase}>Max Thinking Tokens:</label>
              <input
                id="max-thinking-tokens"
                type="number"
                value={tempConfig.claude.env?.MAX_THINKING_TOKENS || ''}
                placeholder="20000"
                onChange={e => handleClaudeEnvChange('MAX_THINKING_TOKENS', e.target.value)}
                className={`${inputBase} ${
                  (initialConfig.claude.env?.MAX_THINKING_TOKENS || '20000') !== (tempConfig.claude.env?.MAX_THINKING_TOKENS || '') ? 'border-warning/40' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="max-output-tokens" className={labelBase}>Max Output Tokens:</label>
              <input
                id="max-output-tokens"
                type="number"
                value={tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || ''}
                placeholder="12000"
                onChange={e => handleClaudeEnvChange('CLAUDE_CODE_MAX_OUTPUT_TOKENS', e.target.value)}
                className={`${inputBase} ${
                  (initialConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '12000') !== (tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '') ? 'border-warning/40' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="autocompact-pct-override" className={labelBase}>Autocompact % Override:</label>
              <input
                id="autocompact-pct-override"
                type="number"
                value={tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || ''}
                placeholder="60"
                onChange={e => handleClaudeEnvChange('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE', e.target.value)}
                className={`${inputBase} ${
                  (initialConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '60') !== (tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '') ? 'border-warning/40' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="no-flicker-mode" className={labelBase}>No-Flicker Mode:</label>
              <select
                id="no-flicker-mode"
                value={tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true'}
                onChange={e => handleClaudeEnvChange('CLAUDE_CODE_NO_FLICKER', e.target.value)}
                className={`${inputBase} ${
                  (initialConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true') !== (tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || '') ? 'border-warning/40' : ''
                }`}
              >
                <option value="true">Enabled — Prevents terminal layout redraws</option>
                <option value="false">Disabled — Forces raw terminal outputs</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Instructions Guide:</label>
              <button
                type="button"
                onClick={() => setShowInstructions(true)}
                className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg transition-all duration-300 cursor-pointer ${
                  isInstructionsModified
                    ? 'border-warning/30 text-warning bg-warning/[0.04] hover:bg-warning/[0.08]'
                    : 'border-white/[0.10] hover:border-accent/30 hover:text-accent bg-white/[0.04]'
                }`}
              >
                <span className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4" />
                  Edit CLAUDE.md Instructions
                </span>
                {isInstructionsModified && (
                  <span className="text-[9px] bg-warning/15 text-warning px-2 py-0.5 rounded font-semibold uppercase tracking-wide">
                    Modified
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Card 2: Security & Permissions */}
        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-2">
          <div className="text-[13px] font-semibold text-[#60a5fa] border-b border-white/[0.08] pb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" /> Security & Permission Policies
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="default-permission-mode" className={labelBase}>Default Permission Mode:</label>
              <select
                id="default-permission-mode"
                value={tempConfig.claude.permissions?.defaultMode || 'ask'}
                onChange={e => handleClaudePermsChange('defaultMode', e.target.value)}
                className={`${inputBase} ${
                  (initialConfig.claude.permissions?.defaultMode || 'ask') !== (tempConfig.claude.permissions?.defaultMode || 'ask') ? 'border-warning/40' : ''
                }`}
              >
                <option value="ask">Ask — Interactive authorization prompts</option>
                <option value="allow">Allow — Auto-approve non-dangerous tasks</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Skip Dangerous Warning:</label>
              <div className="flex items-center h-9">
                <Toggle
                  checked={!!tempConfig.claude.skipDangerousModePermissionPrompt}
                  onChange={() => setTempConfig(prev => prev ? {
                    ...prev,
                    claude: {
                      ...prev.claude,
                      skipDangerousModePermissionPrompt: !prev.claude.skipDangerousModePermissionPrompt
                    }
                  } : null)}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Instructions Modal */}
      {showInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 backdrop-blur-md p-6 animate-fade-in">
          <div className="glass-gold rounded-xl w-full max-w-[900px] h-[80vh] flex flex-col overflow-hidden shadow-2xl shadow-black/40">
            <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.04]">
              <div className="text-[13px] font-semibold text-[#60a5fa] flex items-center gap-2">
                <FileText className="h-4 w-4" /> CLAUDE.md Instructions
              </div>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="text-text-muted hover:text-text-primary cursor-pointer transition-colors p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea
              value={tempConfig.claude_instructions || ''}
              onChange={e => setTempConfig(prev => prev ? { ...prev, claude_instructions: e.target.value } : null)}
              placeholder="# Claude Code Instructions..."
              className="flex-1 w-full bg-bg text-text-secondary font-mono text-[13px] leading-relaxed p-6 border-0 outline-none resize-none focus:ring-0"
            />
            <div className="px-6 py-4 border-t border-white/[0.08] flex items-center justify-between text-[11px] text-text-muted bg-white/[0.03]">
              <span>Press Close to keep staged edits. Changes are saved when you click Apply.</span>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="px-4 py-2 bg-accent/90 hover:bg-accent text-bg font-semibold text-[12px] rounded-lg cursor-pointer transition-all duration-300"
              >
                Close & Stage
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
