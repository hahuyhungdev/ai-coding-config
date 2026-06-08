import React from 'react';
import { Sliders, ShieldCheck, FileText, X } from 'lucide-react';
import type { FullConfig } from '../types';
import { Toggle } from './Toggle';

interface GeminiTabProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const GeminiTab: React.FC<GeminiTabProps> = ({
  initialConfig,
  tempConfig,
  setTempConfig,
}) => {
  const [showInstructions, setShowInstructions] = React.useState(false);
  const isInstructionsModified = initialConfig.gemini_instructions !== tempConfig.gemini_instructions;

  const handleGeminiChange = (key: string, value: any) => {
    setTempConfig(prev => {
      if (!prev) return null;
      return {
        ...prev,
        gemini: {
          ...prev.gemini,
          [key]: value
        }
      };
    });
  };

  const handleWorkspacesChange = (text: string) => {
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
    handleGeminiChange('trustedWorkspaces', lines);
  };

  const trustedWorkspacesText = (tempConfig.gemini.trustedWorkspaces || []).join('\n');

  return (
    <div className="flex flex-col gap-5 max-w-[800px]">
      <div className="text-xs font-bold font-display text-overlay1 uppercase tracking-wider mb-1">
        Antigravity CLI Configuration
      </div>

      <div className="flex flex-col gap-6">
        {/* Card 1: LLM & Environment Configuration */}
        <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-md flex flex-col gap-5">
          <div className="text-base font-bold font-display text-peach border-b border-surface0 pb-2 flex items-center gap-2">
            <Sliders className="h-4 w-4" /> LLM & Environment Configuration
          </div>
          
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Model Alias:</label>
              <input 
                type="text"
                value={tempConfig.gemini.model || ''}
                placeholder="Gemini 3.5 Flash (High)"
                onChange={e => handleGeminiChange('model', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-peach focus:ring-1 focus:ring-peach/30 transition-all ${
                  (initialConfig.gemini.model || '') !== (tempConfig.gemini.model || '') ? 'border-peach' : ''
                }`}
              />
            </div>

            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Enable Telemetry:</label>
              <div className="flex items-center h-9">
                <Toggle 
                  checked={!!tempConfig.gemini.enableTelemetry}
                  onChange={val => handleGeminiChange('enableTelemetry', val)}
                />
              </div>
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
                    : 'border-surface1 hover:border-peach hover:text-peach bg-crust'
                }`}
              >
                <span className="flex items-center gap-2 text-sm">
                  <FileText className="h-4 w-4" />
                  Edit ANTIGRAVITY.md Instructions
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
          <div className="text-base font-bold font-display text-peach border-b border-surface0 pb-2 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4" /> Security & Permission Policies
          </div>

          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className="text-sm font-semibold text-subtext1">Tool Permission Policy:</label>
              <select
                value={tempConfig.gemini.toolPermission || 'always-ask'}
                onChange={e => handleGeminiChange('toolPermission', e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-peach focus:ring-1 focus:ring-peach/30 transition-all ${
                  (initialConfig.gemini.toolPermission || '') !== (tempConfig.gemini.toolPermission || '') ? 'border-peach' : ''
                }`}
              >
                <option value="always-ask">Always Ask (Prompt for permissions)</option>
                <option value="always-proceed">Always Proceed (Auto-approve tools)</option>
              </select>
            </div>

            <div className="grid grid-cols-[200px_1fr] items-start gap-5">
              <label className="text-sm font-semibold text-subtext1 pt-2">Trusted Workspaces:</label>
              <textarea 
                rows={4}
                value={trustedWorkspacesText}
                placeholder="/path/to/project1&#10;/path/to/project2"
                onChange={e => handleWorkspacesChange(e.target.value)}
                className={`w-full bg-crust border border-surface1 text-text text-sm rounded-lg px-3 py-2 outline-none focus:border-peach focus:ring-1 focus:ring-peach/30 transition-all font-mono ${
                  JSON.stringify(initialConfig.gemini.trustedWorkspaces || []) !== JSON.stringify(tempConfig.gemini.trustedWorkspaces || []) ? 'border-peach' : ''
                }`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* INSTRUCTIONS MODAL */}
      {showInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-crust/80 backdrop-blur-sm p-6 animate-fade-in">
          <div className="bg-mantle border border-surface0 rounded-xl w-full max-w-[900px] h-[80vh] flex flex-col overflow-hidden shadow-2xl">
            <div className="bg-surface0 p-4 border-b border-surface1 flex items-center justify-between">
              <div className="text-sm font-bold font-display text-peach flex items-center gap-2">
                <FileText className="h-4 w-4" /> ANTIGRAVITY.md Instructions Guide
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
              value={tempConfig.gemini_instructions || ''}
              onChange={e => setTempConfig(prev => prev ? { ...prev, gemini_instructions: e.target.value } : null)}
              placeholder="# Antigravity CLI Instructions..."
              className="flex-1 w-full bg-[#12131e] text-gray-300 font-mono text-[14px] leading-relaxed p-6 border-0 outline-none resize-none tab-size-4 focus:ring-0"
            />
            <div className="bg-surface0 px-6 py-4 border-t border-surface1 flex items-center justify-between text-xs text-overlay2">
              <span>Press Close to keep staged edits. Changes are saved when you click Apply in the sidebar.</span>
              <button
                type="button"
                onClick={() => setShowInstructions(false)}
                className="px-4 py-2 bg-peach text-crust font-semibold rounded-lg hover:opacity-90 transition-all cursor-pointer"
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

export default GeminiTab;
