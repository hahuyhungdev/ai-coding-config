import React from 'react';
import { Sliders, ShieldCheck, FileText, X } from 'lucide-react';
import type { FullConfig } from '../types';
import { Toggle } from './Toggle';

interface CodexTabProps {
  tempConfig: FullConfig;
  initialConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const CodexTab: React.FC<CodexTabProps> = ({
  tempConfig,
  initialConfig,
  setTempConfig,
}) => {
  const [showInstructions, setShowInstructions] = React.useState(false);

  const handleCodexChange = (key: string, value: any) => {
    setTempConfig(prev => {
      if (!prev) return null;
      return {
        ...prev,
        codex: { ...prev.codex, [key]: value }
      };
    });
  };

  const handleCodexFeatureChange = (key: string, value: boolean) => {
    setTempConfig(prev => {
      if (!prev) return null;
      const features = { ...prev.codex.features, [key]: value };
      return {
        ...prev,
        codex: { ...prev.codex, features }
      };
    });
  };

  const handleCodexNoticeChange = (key: string, value: boolean) => {
    setTempConfig(prev => {
      if (!prev) return null;
      const notice = { ...prev.codex.notice, [key]: value };
      return {
        ...prev,
        codex: { ...prev.codex, notice }
      };
    });
  };

  const isInstructionsModified = initialConfig.codex_instructions !== tempConfig.codex_instructions;

  return (
    <div className="flex flex-col gap-5 max-w-[800px]">
      <div className="text-xs font-bold font-display text-overlay1 uppercase tracking-wider mb-1">
        Codex CLI Configuration
      </div>

      <div className="flex flex-col gap-6">
        
        {/* Card 1: LLM & Environment Configuration */}
        <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-md flex flex-col gap-5">
          <div className="text-base font-bold font-display text-mauve border-b border-surface0 pb-2 flex items-center gap-2">
            <Sliders className="h-4 w-4" /> LLM & Environment Configuration
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Model Alias:</label>
              <input 
                type="text"
                value={tempConfig.codex.model || ''}
                placeholder="gpt-5.5"
                onChange={e => handleCodexChange('model', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.model !== tempConfig.codex.model ? 'border-peach' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Reasoning Effort:</label>
              <select
                value={tempConfig.codex.model_reasoning_effort || 'medium'}
                onChange={e => handleCodexChange('model_reasoning_effort', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.model_reasoning_effort !== tempConfig.codex.model_reasoning_effort ? 'border-peach' : ''
                }`}
              >
                <option value="low">Low (Faster, less context depth)</option>
                <option value="medium">Medium (Standard balanced execution)</option>
                <option value="high">High (Deep thinking, matches complex goals)</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Web Search:</label>
              <select
                value={tempConfig.codex.web_search || 'live'}
                onChange={e => handleCodexChange('web_search', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.web_search !== tempConfig.codex.web_search ? 'border-peach' : ''
                }`}
              >
                <option value="live">Live Web Search (Enabled)</option>
                <option value="disabled">Offline Mode (Disabled)</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-start gap-5">
              <label className="text-sm font-semibold text-subtext1 pt-2">Persistent Instructions:</label>
              <textarea 
                rows={3}
                value={tempConfig.codex.persistent_instructions || ''}
                placeholder="System prompts to force on every initialization..."
                onChange={e => handleCodexChange('persistent_instructions', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all font-mono ${
                  initialConfig.codex.persistent_instructions !== tempConfig.codex.persistent_instructions ? 'border-peach' : ''
                }`}
              />
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
                    : 'border-surface1 hover:border-mauve hover:text-mauve bg-crust'
                }`}
              >
                <span className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4" />
                  Edit AGENTS.md Instructions
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
          <div className="text-base font-bold font-display text-mauve border-b border-surface0 pb-2 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" /> Security & Permission Policies
          </div>
          
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Approval Policy:</label>
              <select
                value={tempConfig.codex.approval_policy || 'on-request'}
                onChange={e => handleCodexChange('approval_policy', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.approval_policy !== tempConfig.codex.approval_policy ? 'border-peach' : ''
                }`}
              >
                <option value="on-request">On Request</option>
                <option value="always">Always</option>
                <option value="never">Never</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Sandbox Mode:</label>
              <select
                value={tempConfig.codex.sandbox_mode || 'workspace-write'}
                onChange={e => handleCodexChange('sandbox_mode', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.sandbox_mode !== tempConfig.codex.sandbox_mode ? 'border-peach' : ''
                }`}
              >
                <option value="workspace-write">Workspace Write</option>
                <option value="read-only">Read Only</option>
                <option value="workspace-read">Workspace Read</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Approvals Reviewer:</label>
              <select
                value={tempConfig.codex.approvals_reviewer || 'user'}
                onChange={e => handleCodexChange('approvals_reviewer', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-mauve focus:ring-1 focus:ring-mauve/30 transition-all ${
                  initialConfig.codex.approvals_reviewer !== tempConfig.codex.approvals_reviewer ? 'border-peach' : ''
                }`}
              >
                <option value="user">User Review (Manual approval)</option>
                <option value="auto">Auto Approve (Bypasses manual checks)</option>
              </select>
            </div>

            {/* Features & Notices Toggles Grid */}
            <div className="border-t border-surface0/60 pt-4 mt-2">
              <div className="text-xs font-bold font-display text-overlay1 tracking-wider uppercase mb-3">
                Features & Warnings
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between p-3 bg-surface0 border border-surface1 rounded-lg">
                  <div>
                    <div className="text-xs font-semibold text-subtext1">Persistent Memories</div>
                    <div className="text-[10px] text-overlay1 mt-0.5">Allow agent to store details</div>
                  </div>
                  <Toggle 
                    checked={!!tempConfig.codex.features?.memories}
                    onChange={val => handleCodexFeatureChange('memories', val)}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-surface0 border border-surface1 rounded-lg">
                  <div>
                    <div className="text-xs font-semibold text-subtext1">Multi-Agent Loops</div>
                    <div className="text-[10px] text-overlay1 mt-0.5">Activate subagent spawning</div>
                  </div>
                  <Toggle 
                    checked={!!tempConfig.codex.features?.multi_agent}
                    onChange={val => handleCodexFeatureChange('multi_agent', val)}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-surface0 border border-surface1 rounded-lg">
                  <div>
                    <div className="text-xs font-semibold text-subtext1">Hide Full Access Notice</div>
                    <div className="text-[10px] text-overlay1 mt-0.5">Bypasses startup prompt</div>
                  </div>
                  <Toggle 
                    checked={!!tempConfig.codex.notice?.hide_full_access_warning}
                    onChange={val => handleCodexNoticeChange('hide_full_access_warning', val)}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-surface0 border border-surface1 rounded-lg">
                  <div>
                    <div className="text-xs font-semibold text-subtext1">Default Opt-out Warning</div>
                    <div className="text-[10px] text-overlay1 mt-0.5">Fast-track opt out warnings</div>
                  </div>
                  <Toggle 
                    checked={!!tempConfig.codex.notice?.fast_default_opt_out}
                    onChange={val => handleCodexNoticeChange('fast_default_opt_out', val)}
                  />
                </div>
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
              <div className="text-sm font-bold font-display text-mauve flex items-center gap-2">
                <FileText className="h-4 w-4" /> AGENTS.md Instructions Guide
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
              value={tempConfig.codex_instructions || ''}
              onChange={e => setTempConfig(prev => prev ? { ...prev, codex_instructions: e.target.value } : null)}
              placeholder="# Codex CLI Instructions..."
              className="flex-1 w-full bg-[#12131e] text-gray-300 font-mono text-[14px] leading-relaxed p-6 border-0 outline-none resize-none tab-size-4 focus:ring-0"
            />
            <div className="bg-surface0 px-6 py-4 border-t border-surface1 flex items-center justify-between text-xs text-overlay2">
              <span>Press Close to keep staged edits. Changes are saved when you click Apply in the sidebar.</span>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="px-4 py-2 bg-mauve text-crust font-semibold rounded-lg hover:opacity-90 transition-all cursor-pointer"
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

export default CodexTab;
