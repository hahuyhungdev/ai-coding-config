import React from 'react';
import { Sliders, ShieldCheck, FileText, X } from 'lucide-react';
import type { FullConfig } from '../../../../types';
import { Toggle } from '../../../../components/Toggle';

interface CodexTabProps {
  tempConfig: FullConfig;
  initialConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const CodexTab: React.FC<CodexTabProps> = ({ tempConfig, initialConfig, setTempConfig }) => {
  const [showInstructions, setShowInstructions] = React.useState(false);

  const handleCodexChange = (key: string, value: any) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, [key]: value } } : null);
  };
  const handleCodexFeatureChange = (key: string, value: boolean) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, features: { ...prev.codex.features, [key]: value } } } : null);
  };
  const handleCodexNoticeChange = (key: string, value: boolean) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, notice: { ...prev.codex.notice, [key]: value } } } : null);
  };

  const isInstructionsModified = initialConfig.codex_instructions !== tempConfig.codex_instructions;
  const inputBase = "w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-sm rounded-lg px-3 py-2 outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300";
  const labelBase = "text-sm font-medium text-text-secondary";
  const accentColor = "text-success";

  return (
    <div className="flex flex-col gap-5 w-full">
      <div>
        <h2 className="font-display text-2xl text-text-primary mb-1">Codex CLI</h2>
        <p className="text-sm text-text-muted">Configure model, security, and agent behavior</p>
      </div>

      <div className="flex flex-col gap-5">
        {/* LLM & Environment */}
        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-1">
          <div className={`text-[13px] font-semibold ${accentColor} border-b border-white/[0.08] pb-3 flex items-center gap-2`}>
            <Sliders className="h-4 w-4" /> LLM & Environment
          </div>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-model-alias" className={labelBase}>Model Alias:</label>
              <input id="codex-model-alias" type="text" value={tempConfig.codex.model || ''} placeholder="gpt-5.5" onChange={e => handleCodexChange('model', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.model !== tempConfig.codex.model ? 'border-warning/40' : ''}`} />
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-reasoning-effort" className={labelBase}>Reasoning Effort:</label>
              <select id="codex-reasoning-effort" value={tempConfig.codex.model_reasoning_effort || 'medium'} onChange={e => handleCodexChange('model_reasoning_effort', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.model_reasoning_effort !== tempConfig.codex.model_reasoning_effort ? 'border-warning/40' : ''}`}>
                <option value="low">Low — Faster, less depth</option>
                <option value="medium">Medium — Balanced execution</option>
                <option value="high">High — Deep thinking for complex goals</option>
              </select>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-web-search" className={labelBase}>Web Search:</label>
              <select id="codex-web-search" value={tempConfig.codex.web_search || 'live'} onChange={e => handleCodexChange('web_search', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.web_search !== tempConfig.codex.web_search ? 'border-warning/40' : ''}`}>
                <option value="live">Live — Enabled</option>
                <option value="disabled">Offline — Disabled</option>
              </select>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-start gap-5">
              <label htmlFor="codex-persistent-instructions" className={`${labelBase} pt-2`}>Persistent Instructions:</label>
              <textarea id="codex-persistent-instructions" rows={3} value={tempConfig.codex.persistent_instructions || ''} placeholder="System prompts for every init..." onChange={e => handleCodexChange('persistent_instructions', e.target.value)}
                className={`${inputBase} font-mono resize-none ${initialConfig.codex.persistent_instructions !== tempConfig.codex.persistent_instructions ? 'border-warning/40' : ''}`} />
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label className={labelBase}>Instructions:</label>
              <button type="button" onClick={() => setShowInstructions(true)}
                className={`w-full flex items-center justify-between px-3 py-2 border rounded-lg transition-all duration-300 cursor-pointer ${
                  isInstructionsModified ? 'border-warning/30 text-warning bg-warning/[0.04]' : 'border-white/[0.10] hover:border-accent/30 hover:text-accent bg-white/[0.04]'
                }`}>
                <span className="flex items-center gap-2 text-sm"><FileText className="h-4 w-4" /> Edit AGENTS.md</span>
                {isInstructionsModified && <span className="text-[9px] bg-warning/15 text-warning px-2 py-0.5 rounded font-semibold uppercase">Modified</span>}
              </button>
            </div>
          </div>
        </div>

        {/* Security & Permissions */}
        <div className="glass rounded-xl p-6 flex flex-col gap-5 animate-fade-up stagger-2">
          <div className={`text-[13px] font-semibold ${accentColor} border-b border-white/[0.08] pb-3 flex items-center gap-2`}>
            <ShieldCheck className="h-4 w-4" /> Security & Permissions
          </div>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-approval-policy" className={labelBase}>Approval Policy:</label>
              <select id="codex-approval-policy" value={tempConfig.codex.approval_policy || 'on-request'} onChange={e => handleCodexChange('approval_policy', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.approval_policy !== tempConfig.codex.approval_policy ? 'border-warning/40' : ''}`}>
                <option value="on-request">On Request</option>
                <option value="always">Always</option>
                <option value="never">Never</option>
              </select>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-sandbox-mode" className={labelBase}>Sandbox Mode:</label>
              <select id="codex-sandbox-mode" value={tempConfig.codex.sandbox_mode || 'workspace-write'} onChange={e => handleCodexChange('sandbox_mode', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.sandbox_mode !== tempConfig.codex.sandbox_mode ? 'border-warning/40' : ''}`}>
                <option value="workspace-write">Workspace Write</option>
                <option value="read-only">Read Only</option>
                <option value="workspace-read">Workspace Read</option>
              </select>
            </div>
            <div className="grid grid-cols-[200px_1fr] items-center gap-5">
              <label htmlFor="codex-approvals-reviewer" className={labelBase}>Approvals Reviewer:</label>
              <select id="codex-approvals-reviewer" value={tempConfig.codex.approvals_reviewer || 'user'} onChange={e => handleCodexChange('approvals_reviewer', e.target.value)}
                className={`${inputBase} ${initialConfig.codex.approvals_reviewer !== tempConfig.codex.approvals_reviewer ? 'border-warning/40' : ''}`}>
                <option value="user">User — Manual approval</option>
                <option value="auto">Auto — Bypass manual checks</option>
              </select>
            </div>

            {/* Feature toggles */}
            <div className="border-t border-white/[0.08] pt-4 mt-2">
              <div className="text-[10px] font-semibold text-text-muted tracking-[0.15] uppercase mb-3">Features & Warnings</div>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { key: 'memories', label: 'Persistent Memories', desc: 'Allow agent to store details', checked: !!tempConfig.codex.features?.memories, onChange: (v: boolean) => handleCodexFeatureChange('memories', v) },
                  { key: 'multi_agent', label: 'Multi-Agent Loops', desc: 'Activate subagent spawning', checked: !!tempConfig.codex.features?.multi_agent, onChange: (v: boolean) => handleCodexFeatureChange('multi_agent', v) },
                  { key: 'hide_warn', label: 'Hide Full Access Notice', desc: 'Bypasses startup prompt', checked: !!tempConfig.codex.notice?.hide_full_access_warning, onChange: (v: boolean) => handleCodexNoticeChange('hide_full_access_warning', v) },
                  { key: 'opt_out', label: 'Default Opt-out Warning', desc: 'Fast-track opt out warnings', checked: !!tempConfig.codex.notice?.fast_default_opt_out, onChange: (v: boolean) => handleCodexNoticeChange('fast_default_opt_out', v) },
                ].map(item => (
                  <div key={item.key} className="flex items-center justify-between p-3 bg-white/[0.04] border border-white/[0.08] rounded-lg">
                    <div>
                      <div className="text-xs font-medium text-text-secondary">{item.label}</div>
                      <div className="text-[10px] text-text-muted mt-0.5">{item.desc}</div>
                    </div>
                    <Toggle checked={item.checked} onChange={item.onChange} />
                  </div>
                ))}
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
              <div className={`text-[13px] font-semibold ${accentColor} flex items-center gap-2`}>
                <FileText className="h-4 w-4" /> AGENTS.md Instructions
              </div>
              <button type="button" onClick={() => setShowInstructions(false)} className="text-text-muted hover:text-text-primary cursor-pointer transition-colors p-1">
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea value={tempConfig.codex_instructions || ''} onChange={e => setTempConfig(prev => prev ? { ...prev, codex_instructions: e.target.value } : null)}
              placeholder="# Codex CLI Instructions..." className="flex-1 w-full bg-bg text-text-secondary font-mono text-[13px] leading-relaxed p-6 border-0 outline-none resize-none focus:ring-0" />
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

export default CodexTab;
