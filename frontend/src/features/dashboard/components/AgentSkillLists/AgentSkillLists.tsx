import React from 'react';
import { Bot, Wrench } from 'lucide-react';
import type { FullConfig } from '../../../../types';

interface AgentSkillListsProps {
  tempConfig: FullConfig;
  setActiveTab: (tab: string) => void;
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
}

export const AgentSkillLists: React.FC<AgentSkillListsProps> = ({
  tempConfig,
  setActiveTab,
  setExplorerFilter,
  setSelectedExplorer
}) => {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-up stagger-3">
      {/* Agents Block */}
      <div className="glass rounded-xl p-5 flex flex-col border border-white/[0.08]">
        <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-white/[0.06]">
          <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
            <Bot className="h-4 w-4 text-info" />
            <span>Agents ({tempConfig.agents.length})</span>
          </h4>
          <button
            onClick={() => { setExplorerFilter('agents'); setActiveTab('explorer'); }}
            className="text-[10px] text-info hover:text-info/80 font-bold transition-colors cursor-pointer"
          >
            View All →
          </button>
        </div>
        <div className="flex flex-col gap-2 max-h-[190px] overflow-y-auto pr-1">
          {tempConfig.agents.slice(0, 3).map(agentName => (
            <div
              key={agentName}
              onClick={() => { setSelectedExplorer({ type: 'agent', name: agentName }); setActiveTab('explorer'); }}
              className="flex items-center justify-between p-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] hover:border-info/35 rounded-lg cursor-pointer transition-all duration-300 group"
            >
              <span className="text-xs font-mono text-text-primary font-semibold group-hover:text-info transition-colors">{agentName}</span>
              <span className="text-[9px] px-2 py-0.5 rounded-md bg-info-dim text-info border border-info/15 font-bold uppercase tracking-wider">Agent</span>
            </div>
          ))}
          {tempConfig.agents.length === 0 && (
            <div className="text-[11px] text-text-muted text-center py-6">No agents configured</div>
          )}
        </div>
      </div>

      {/* Skills Block */}
      <div className="glass rounded-xl p-5 flex flex-col border border-white/[0.08]">
        <div className="flex items-center justify-between pb-3.5 mb-3.5 border-b border-white/[0.06]">
          <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-2">
            <Wrench className="h-4 w-4 text-accent" />
            <span>Skills ({tempConfig.skills.length})</span>
          </h4>
          <button
            onClick={() => { setExplorerFilter('skills'); setActiveTab('explorer'); }}
            className="text-[10px] text-accent hover:text-accent/80 font-bold transition-colors cursor-pointer"
          >
            View All →
          </button>
        </div>
        <div className="flex flex-col gap-2 max-h-[190px] overflow-y-auto pr-1">
          {tempConfig.skills.slice(0, 3).map(skillName => (
            <div
              key={skillName}
              onClick={() => { setSelectedExplorer({ type: 'skill', name: skillName }); setActiveTab('explorer'); }}
              className="flex items-center justify-between p-3 bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] hover:border-accent/35 rounded-lg cursor-pointer transition-all duration-300 group"
            >
              <span className="text-xs font-mono text-text-primary font-semibold group-hover:text-accent transition-colors">{skillName}</span>
              <span className="text-[9px] px-2 py-0.5 rounded-md bg-accent-dim text-accent border border-accent/15 font-bold uppercase tracking-wider">Skill</span>
            </div>
          ))}
          {tempConfig.skills.length === 0 && (
            <div className="text-[11px] text-text-muted text-center py-6">No skills configured</div>
          )}
        </div>
      </div>
    </div>
  );
};
