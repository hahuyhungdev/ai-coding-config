import React from 'react';
import { MessageSquareCode, Terminal as TerminalIcon, Sparkles } from 'lucide-react';
import type { FullConfig } from '../../../../types';

interface TargetCardsProps {
  tempConfig: FullConfig;
}

const CLI_CONFIGS: Record<string, { name: string; description: string; icon: React.ReactNode }> = {
  claude: {
    name: "Claude Code",
    description: "Configures templates and prompt options for Anthropic's Claude Code CLI tool.",
    icon: <MessageSquareCode className="h-5 w-5 text-info" />
  },
  codex: {
    name: "Codex CLI",
    description: "Manages system instructions, command aliases, and model parameters for Codex CLI.",
    icon: <TerminalIcon className="h-5 w-5 text-success" />
  },
  agy: {
    name: "Antigravity",
    description: "Configures Google Antigravity custom skills, rules, workspace agents, and integrations.",
    icon: <Sparkles className="h-5 w-5 text-accent" />
  }
};

export const TargetCards: React.FC<TargetCardsProps> = ({ tempConfig }) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-up stagger-1">
      {Object.entries(CLI_CONFIGS).map(([cid, info]) => {
        const tempVal = tempConfig.targets[cid];
        return (
          <div
            key={cid}
            className={`group relative rounded-xl p-5 overflow-hidden transition-all duration-300 hover-lift border ${
              tempVal
                ? 'glass-gold border-accent/25 bg-gradient-to-br from-accent/5 to-transparent'
                : 'glass border-white/[0.08] opacity-60 hover:opacity-80'
            }`}
          >
            {/* Elegant top accent line for active cards */}
            {tempVal && (
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-accent/50 to-transparent" />
            )}

            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Target CLI</span>
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] font-semibold text-text-muted">
                  {tempVal ? 'Staged' : 'Excluded'}
                </span>
                <span
                  className={`h-2.5 w-2.5 rounded-full transition-all duration-300 ${
                    tempVal
                      ? 'bg-success shadow-[0_0_8px_rgba(5,150,105,0.4)] animate-pulse'
                      : 'bg-text-muted/30'
                  }`}
                />
              </div>
            </div>

            <div className="flex items-center gap-3 mb-2.5">
              <div className={`p-2 rounded-lg ${tempVal ? 'bg-white/10 dark:bg-black/10' : 'bg-white/5'}`}>
                {info.icon}
              </div>
              <h3 className="text-[15px] font-semibold text-text-primary tracking-wide">
                {info.name}
              </h3>
            </div>

            <p className="text-[11px] text-text-muted leading-relaxed min-h-[32px]">
              {tempVal ? "Staged to sync templates and options on next config install." : "Excluded from synchronization."}
            </p>
          </div>
        );
      })}
    </div>
  );
};
