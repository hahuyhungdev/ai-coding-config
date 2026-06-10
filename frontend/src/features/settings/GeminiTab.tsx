import React from 'react';
import { Sliders, ShieldCheck, FileText, X } from 'lucide-react';
import type { FullConfig } from '../../types';
import { Toggle } from '../../components/Toggle';

interface GeminiTabProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const GeminiTab: React.FC<GeminiTabProps> = ({ initialConfig, tempConfig, setTempConfig }) => {
  const [showInstructions, setShowInstructions] = React.useState(false);
  const isInstructionsModified = initialConfig.gemini_instructions !== tempConfig.gemini_instructions;

  const handleGeminiChange = (key: string, value: any) => {
    setTempConfig(prev => prev ? { ...prev, gemini: { ...prev.gemini, [key]: value } } : null);
  };
  const handleWorkspacesChange = (text: string) => {
    handleGeminiChange('trustedWorkspaces', text.split('\n').map(l => l.trim()).filter(Boolean));
  };

  const trustedWorkspacesText = (tempConfig.gemini.trustedWorkspaces || []).join('\n');
  const inputBase = "w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300";
  const labelBase = "text-sm font-medium text-text-secondary";
  const accentColor = "text-[#f59e0b]";

  return (
    <div className="flex flex-col gap-5 max-w-[800px]">
      <div>
        <h2 className="font-display text-2xl text-text-primary mb-1">Antigravity CLI</h2>
        <p className="text-sm text-text-muted">Configure Gemini model and workspace trust</p>
      </div>

      <div className="flex flex-col gap-5">
        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-1">
          <div className={`text-[13px] font-semibold ${accentColor} border-b border-white/[0.08] pb-3 flex items-center gap-2`}>
            <Sliders className="h-4 w-4" /> LLM & Environment
          </div>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Model Alias:</label>
              <input type="text" value={tempConfig.gemini.model || ''} placeholder="Gemini 3.5 Flash" onChange={e => handleGeminiChange('model', e.target.value)}
                className={`${inputBase} ${(initialConfig.gemini.model || '') !== (tempConfig.gemini.model || '') ? 'border-warning/40' : ''}`} />
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Enable Telemetry:</label>
              <div className="flex items-center h-9">
                <Toggle checked={!!tempConfig.gemini.enableTelemetry} onChange={val => handleGeminiChange('enableTelemetry', val)} />
              </div>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Instructions:</label>
              <button type="button" onClick={() => setShowInstructions(true)}
                className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg transition-all duration-300 cursor-pointer ${
                  isInstructionsModified ? 'border-warning/30 text-warning bg-warning/[0.04]' : 'border-white/[0.10] hover:border-accent/30 hover:text-accent bg-white/[0.04]'
                }`}>
                <span className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4" /> Edit ANTIGRAVITY.md</span>
                {isInstructionsModified && <span className="text-[9px] bg-warning/15 text-warning px-2 py-0.5 rounded font-semibold uppercase">Modified</span>}
              </button>
            </div>
          </div>
        </div>

        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-2">
          <div className={`text-[13px] font-semibold ${accentColor} border-b border-white/[0.08] pb-3 flex items-center gap-2`}>
            <ShieldCheck className="h-4 w-4" /> Security & Permissions
          </div>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Tool Permission:</label>
              <select value={tempConfig.gemini.toolPermission || 'always-ask'} onChange={e => handleGeminiChange('toolPermission', e.target.value)}
                className={`${inputBase} ${(initialConfig.gemini.toolPermission || '') !== (tempConfig.gemini.toolPermission || '') ? 'border-warning/40' : ''}`}>
                <option value="always-ask">Always Ask — Prompt for permissions</option>
                <option value="always-proceed">Always Proceed — Auto-approve tools</option>
              </select>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-start gap-5">
              <label className={`${labelBase} pt-2`}>Trusted Workspaces:</label>
              <textarea rows={4} value={trustedWorkspacesText} placeholder="/path/to/project1\n/path/to/project2" onChange={e => handleWorkspacesChange(e.target.value)}
                className={`${inputBase} font-mono resize-none ${JSON.stringify(initialConfig.gemini.trustedWorkspaces || []) !== JSON.stringify(tempConfig.gemini.trustedWorkspaces || []) ? 'border-warning/40' : ''}`} />
            </div>
          </div>
        </div>
      </div>

      {showInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg/80 backdrop-blur-md p-6 animate-fade-in">
          <div className="glass-gold rounded-xl w-full max-w-[900px] h-[80vh] flex flex-col overflow-hidden shadow-2xl shadow-black/40">
            <div className="p-4 border-b border-white/[0.08] flex items-center justify-between bg-white/[0.04]">
              <div className={`text-[13px] font-semibold ${accentColor} flex items-center gap-2`}>
                <FileText className="h-4 w-4" /> ANTIGRAVITY.md Instructions
              </div>
              <button type="button" onClick={() => setShowInstructions(false)} className="text-text-muted hover:text-text-primary cursor-pointer transition-colors p-1">
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea value={tempConfig.gemini_instructions || ''} onChange={e => setTempConfig(prev => prev ? { ...prev, gemini_instructions: e.target.value } : null)}
              placeholder="# Antigravity CLI Instructions..." className="flex-1 w-full bg-bg text-text-secondary font-mono text-[13px] leading-relaxed p-6 border-0 outline-none resize-none focus:ring-0" />
            <div className="px-6 py-4 border-t border-white/[0.08] flex items-center justify-between text-[11px] text-text-muted bg-white/[0.03]">
              <span>Press Close to keep staged edits. Changes are saved when you click Apply.</span>
              <button type="button" onClick={() => setShowInstructions(false)} className="px-4 py-2 bg-accent/90 hover:bg-accent text-bg font-semibold text-[12px] rounded-lg cursor-pointer transition-all duration-300">
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
