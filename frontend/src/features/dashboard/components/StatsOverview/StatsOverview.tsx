import React from 'react';
import { Bot, Wrench, Cpu } from 'lucide-react';
import type { FullConfig } from '../../../../types';

interface StatsOverviewProps {
  tempConfig: FullConfig;
  setActiveTab: (tab: string) => void;
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({
  tempConfig,
  setActiveTab,
  setExplorerFilter
}) => {
  const activeMcpCount = tempConfig.all_mcp.length - tempConfig.disabled_mcp.length;
  const disabledMcpCount = tempConfig.disabled_mcp.length;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5 animate-fade-up stagger-2">
      {/* Agents Stat */}
      <div
        onClick={() => { setExplorerFilter('agents'); setActiveTab('explorer'); }}
        className="glass rounded-xl p-4.5 flex items-center gap-4 cursor-pointer hover-lift group border border-white/[0.08]"
      >
        <div className="h-11 w-11 rounded-xl bg-info-dim border border-info/15 flex items-center justify-center group-hover:border-info/30 group-hover:bg-info-dim/80 transition-all duration-300">
          <Bot className="h-5.5 w-5.5 text-info" />
        </div>
        <div>
          <div className="text-[10px] text-text-muted uppercase font-bold tracking-wider">Agents</div>
          <div className="text-2xl font-display font-semibold text-text-primary mt-0.5">
            {tempConfig.agents.length}
          </div>
        </div>
      </div>

      {/* Skills Stat */}
      <div
        onClick={() => { setExplorerFilter('skills'); setActiveTab('explorer'); }}
        className="glass rounded-xl p-4.5 flex items-center gap-4 cursor-pointer hover-lift group border border-white/[0.08]"
      >
        <div className="h-11 w-11 rounded-xl bg-accent-dim border border-accent/15 flex items-center justify-center group-hover:border-accent/30 group-hover:bg-accent-dim/80 transition-all duration-300">
          <Wrench className="h-5.5 w-5.5 text-accent" />
        </div>
        <div>
          <div className="text-[10px] text-text-muted uppercase font-bold tracking-wider">Skills</div>
          <div className="text-2xl font-display font-semibold text-text-primary mt-0.5">
            {tempConfig.skills.length}
          </div>
        </div>
      </div>

      {/* MCP Servers Stat */}
      <div
        onClick={() => setActiveTab('mcp')}
        className="glass rounded-xl p-4.5 flex items-center gap-4 cursor-pointer hover-lift group col-span-1 sm:col-span-2 border border-white/[0.08]"
      >
        <div className="h-11 w-11 rounded-xl bg-accent-dim border border-accent-glow flex items-center justify-center group-hover:border-accent-dim transition-all duration-300">
          <Cpu className="h-5.5 w-5.5 text-accent" />
        </div>
        <div className="flex-1">
          <div className="text-[10px] text-text-muted uppercase font-bold tracking-wider">MCP Servers</div>
          <div className="text-[14px] font-semibold text-text-primary mt-1.5 flex items-center gap-2">
            <span className="text-success flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
              {activeMcpCount} Active
            </span>
            <span className="text-text-muted/40">|</span>
            <span className="text-text-muted flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-text-muted/40" />
              {disabledMcpCount} Disabled
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
