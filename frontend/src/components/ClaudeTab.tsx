import React from 'react';
import type { FullConfig } from '../types';
import { Toggle } from './Toggle';
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

  return (
    <div className="flex flex-col gap-5 max-w-[800px]">
      <div className="text-xs font-bold font-display text-overlay1 uppercase tracking-wider mb-1">
        Claude Code Configuration
      </div>

      <div className="flex flex-col gap-6">
        {/* Card 1: LLM & Environment Configuration */}
        <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-md flex flex-col gap-5">
          <div className="text-base font-bold font-display text-blue border-b border-surface0 pb-2 flex items-center gap-2">
            <Sliders className="h-4 w-4" /> LLM & Environment Configuration
          </div>
          
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Max Thinking Tokens:</label>
              <input 
                type="number"
                value={tempConfig.claude.env?.MAX_THINKING_TOKENS || ''}
                placeholder="20000"
                onChange={e => handleClaudeEnvChange('MAX_THINKING_TOKENS', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all ${
                  (initialConfig.claude.env?.MAX_THINKING_TOKENS || '20000') !== (tempConfig.claude.env?.MAX_THINKING_TOKENS || '') ? 'border-peach' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Max Output Tokens:</label>
              <input 
                type="number"
                value={tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || ''}
                placeholder="12000"
                onChange={e => handleClaudeEnvChange('CLAUDE_CODE_MAX_OUTPUT_TOKENS', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all ${
                  (initialConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '12000') !== (tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '') ? 'border-peach' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Autocompact % Override:</label>
              <input 
                type="number"
                value={tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || ''}
                placeholder="60"
                onChange={e => handleClaudeEnvChange('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all ${
                  (initialConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '60') !== (tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '') ? 'border-peach' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">No-Flicker Mode:</label>
              <select
                value={tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true'}
                onChange={e => handleClaudeEnvChange('CLAUDE_CODE_NO_FLICKER', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all ${
                  (initialConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true') !== (tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || '') ? 'border-peach' : ''
                }`}
              >
                <option value="true">Enabled (Prevents terminal layout redraws)</option>
                <option value="false">Disabled (Forces raw terminal outputs)</option>
              </select>
            </div>

            {/* Instructions Guide Button Row */}
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Instructions Guide:</label>
              <button
                type="button"
                onClick={() => setShowInstructions(true)}
                className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg transition-all duration-200 cursor-pointer ${
                  isInstructionsModified 
                    ? 'border-peach text-peach bg-peach/5 hover:bg-peach/10' 
                    : 'border-surface1 hover:border-blue hover:text-blue bg-crust'
                }`}
              >
                <span className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4" />
                  Edit CLAUDE.md Instructions
                </span>
                {isInstructionsModified && (
                  <span className="text-[10px] bg-peach/20 px-2 py-0.5 rounded font-bold font-display uppercase tracking-wide">
                    Modified
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Card 2: Security & Permission Policies */}
        <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-md flex flex-col gap-5">
          <div className="text-base font-bold font-display text-blue border-b border-surface0 pb-2 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" /> Security & Permission Policies
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Default Permission Mode:</label>
              <select
                value={tempConfig.claude.permissions?.defaultMode || 'ask'}
                onChange={e => handleClaudePermsChange('defaultMode', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-blue focus:ring-1 focus:ring-blue/30 transition-all ${
                  (initialConfig.claude.permissions?.defaultMode || 'ask') !== (tempConfig.claude.permissions?.defaultMode || 'ask') ? 'border-peach' : ''
                }`}
              >
                <option value="ask">Ask (Interactive authorization prompts)</option>
                <option value="allow">Allow (Auto-approve non-dangerous tasks)</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Skip Dangerous Warning:</label>
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

      {/* INSTRUCTIONS MODAL */}
      {showInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-crust/80 backdrop-blur-sm p-6 animate-fade-in">
          <div className="bg-mantle border border-surface0 rounded-xl w-full max-w-[900px] h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="bg-surface0 p-4 border-b border-surface1 flex items-center justify-between">
              <div className="text-sm font-bold font-display text-blue flex items-center gap-2">
                <FileText className="h-4 w-4" /> CLAUDE.md Instructions Guide
              </div>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="text-overlay2 hover:text-text cursor-pointer transition-colors p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea
              value={tempConfig.claude_instructions || ''}
              onChange={e => setTempConfig(prev => prev ? { ...prev, claude_instructions: e.target.value } : null)}
              placeholder="# Claude Code Instructions..."
              className="flex-1 w-full bg-[#12131e] text-gray-300 font-mono text-[14px] leading-relaxed p-6 border-0 outline-none resize-none tab-size-4 focus:ring-0"
            />
            <div className="bg-surface0 px-6 py-4 border-t border-surface1 flex items-center justify-between text-xs text-overlay2">
              <span>Press Close to keep staged edits. Changes are saved when you click Apply in the sidebar.</span>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="px-4 py-2 bg-blue text-crust font-semibold rounded-lg hover:opacity-90 transition-all cursor-pointer"
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
