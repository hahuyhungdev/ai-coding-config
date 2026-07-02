import React, { useState } from 'react';
import type { FullConfig } from '../../types';
import { GraphifyStatus } from './components/GraphifyStatus/GraphifyStatus';
import { TargetCards } from './components/TargetCards/TargetCards';
import { StatsOverview } from './components/StatsOverview/StatsOverview';
import { AgentSkillLists } from './components/AgentSkillLists/AgentSkillLists';
import { LogTerminal } from './components/LogTerminal/LogTerminal';

interface DashboardTabProps {
  tempConfig: FullConfig;
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  setActiveTab: (tab: string) => void;
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
  fetchConfig?: () => Promise<void>;
}

export const DashboardTab: React.FC<DashboardTabProps> = ({
  tempConfig,
  logs,
  setLogs,
  setActiveTab,
  setExplorerFilter,
  setSelectedExplorer,
  fetchConfig
}) => {
  const [rebuilding, setRebuilding] = useState(false);

  const handleRebuildGraph = async () => {
    setRebuilding(true);
    setLogs(prev => [...prev, "🔄 Triggering Graphify rebuild for active repository..."]);
    try {
      const res = await fetch('/api/graphify/rebuild', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setLogs(prev => [
          ...prev,
          "✓ Graphify index successfully updated!",
          `Output: ${data.stdout || ''}`,
          `Graph Size: ${data.health?.graph_size_kb || 0} KB`,
          `Commit: ${data.health?.build_commit || 'N/A'}`
        ]);
        if (fetchConfig) {
          await fetchConfig();
        }
      } else {
        setLogs(prev => [
          ...prev,
          `✘ Rebuild failed!`,
          `Error: ${data.stderr || data.detail || 'Unknown error'}`
        ]);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setLogs(prev => [...prev, `✘ Network error: ${errMsg}`]);
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Hero greeting */}
      <div className="animate-fade-up">
        <h2 className="font-display text-3xl font-bold text-text-primary mb-1 tracking-tight">
          Dashboard
        </h2>
        <p className="text-sm text-text-muted">
          Manage your AI coding configuration across CLI targets
        </p>
      </div>

      {/* Graphify Health Status Alert */}
      <GraphifyStatus
        tempConfig={tempConfig}
        rebuilding={rebuilding}
        onRebuild={handleRebuildGraph}
      />

      {/* Target status cards */}
      <TargetCards tempConfig={tempConfig} />

      {/* Stats overview */}
      <StatsOverview
        tempConfig={tempConfig}
        setActiveTab={setActiveTab}
        setExplorerFilter={setExplorerFilter}
      />

      {/* Agents & Skills lists */}
      <AgentSkillLists
        tempConfig={tempConfig}
        setActiveTab={setActiveTab}
        setExplorerFilter={setExplorerFilter}
        setSelectedExplorer={setSelectedExplorer}
      />

      {/* Logs terminal */}
      <LogTerminal
        logs={logs}
        setLogs={setLogs}
      />
    </div>
  );
};
