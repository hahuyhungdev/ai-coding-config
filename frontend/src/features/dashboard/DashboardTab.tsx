import React, { useRef, useEffect } from 'react';
import type { FullConfig } from '../../types';
import {
  MessageSquareCode, Terminal as TerminalIcon, Sparkles,
  Bot, Wrench, Cpu, Trash, AlertTriangle, CheckCircle2, RefreshCw
} from 'lucide-react';

interface DashboardTabProps {
  tempConfig: FullConfig;
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  setActiveTab: (tab: string) => void;
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
  fetchConfig?: () => Promise<void>;
}

const CLI_CONFIGS: Record<string, { name: string; icon: string }> = {
  claude: { name: "Claude Code", icon: "message-square-code" },
  codex: { name: "Codex CLI", icon: "terminal" },
  agy: { name: "Antigravity", icon: "sparkles" }
};

export const DashboardTab: React.FC<DashboardTabProps> = ({
  tempConfig,
  logs,
  setLogs,
  setActiveTab,
  setExplorerFilter,
  setSelectedExplorer,
  fetchConfig
}) => {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [rebuilding, setRebuilding] = React.useState(false);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

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
    } catch (err: any) {
      setLogs(prev => [...prev, `✘ Network error: ${err.message}`]);
    } finally {
      setRebuilding(false);
    }
  };

  const ansiToHtml = (text: string) => {
    const ansiMap: Record<string, string> = {
      '31': 'text-error font-bold',
      '32': 'text-success font-bold',
      '33': 'text-warning font-bold',
      '34': 'text-info font-bold',
      '35': 'text-accent font-bold',
      '36': 'text-info font-bold',
      '90': 'text-text-muted',
      '91': 'text-error',
      '92': 'text-success',
      '93': 'text-warning',
      '94': 'text-info',
    };

    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const regex = /\x1B\[(\d+(?:;\d+)*)m/g;
    let openSpans = 0;

    html = html.replace(regex, (_, codes) => {
      let replacement = '';
      const codeArray = codes.split(';');
      for (const code of codeArray) {
        if (code === '0') {
          while (openSpans > 0) {
            replacement += '</span>';
            openSpans--;
          }
        } else if (ansiMap[code]) {
          replacement += `<span class="${ansiMap[code]}">`;
          openSpans++;
        }
      }
      return replacement;
    });

    while (openSpans > 0) {
      html += '</span>';
      openSpans--;
    }

    return <div dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Hero greeting */}
      <div className="animate-fade-up">
        <h2 className="font-display text-3xl text-text-primary mb-1">Dashboard</h2>
        <p className="text-sm text-text-muted">Manage your AI coding configuration across CLI targets</p>
      </div>

      {/* Graphify Health Status Alert */}
      {tempConfig.graphify_health && (
        <div className={`rounded-lg p-4 border animate-fade-up flex items-start justify-between gap-4 ${
          !tempConfig.graphify_health.graph_exists
            ? 'bg-error/10 border-error/20 text-error'
            : tempConfig.graphify_health.is_stale
              ? 'bg-warning/10 border-warning/20 text-warning'
              : 'bg-success/5 border-success/15 text-success'
        }`}>
          <div className="flex items-start gap-3">
            <div className="mt-0.5">
              {!tempConfig.graphify_health.graph_exists ? (
                <AlertTriangle size={18} className="text-error animate-pulse" />
              ) : tempConfig.graphify_health.is_stale ? (
                <AlertTriangle size={18} className="text-warning" />
              ) : (
                <CheckCircle2 size={18} className="text-success" />
              )}
            </div>
            <div>
              <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
                {!tempConfig.graphify_health.graph_exists
                  ? 'Graphify Index Missing'
                  : tempConfig.graphify_health.is_stale
                    ? 'Graphify Index Stale'
                    : 'Graphify Index Healthy'}
                <span className="text-[10px] opacity-75 font-mono">
                  {tempConfig.graphify_health.graph_exists ? `(${tempConfig.graphify_health.graph_size_kb} KB)` : ''}
                </span>
              </h4>
              <p className="text-[12px] opacity-80 leading-relaxed">
                {!tempConfig.graphify_health.graph_exists
                  ? 'Your codebase has not been semantic-indexed yet. Run the installer or trigger a rebuild to initialize the Graphify index.'
                  : tempConfig.graphify_health.is_stale
                    ? `${tempConfig.graphify_health.stale_reason} Trigger a rebuild to refresh the index.`
                    : `Active Graphify index is synchronized with commit ${tempConfig.graphify_health.current_commit}. Last built: ${tempConfig.graphify_health.last_built}`}
              </p>
              {tempConfig.graphify_health.graph_exists && !tempConfig.graphify_health.git_hooks_installed && (
                <div className="mt-2 text-[11px] font-medium text-warning flex items-center gap-1.5">
                  <AlertTriangle size={12} /> Git hooks are not fully configured. Background auto-updates will not trigger.
                </div>
              )}
            </div>
          </div>
          {tempConfig.graphify_health.graph_exists && (
            <button
              disabled={rebuilding}
              onClick={handleRebuildGraph}
              className={`px-3 py-1.5 text-[11px] font-semibold rounded-md transition-all cursor-pointer flex items-center gap-1.5 border shrink-0 ${
                rebuilding
                  ? 'bg-text-muted/10 border-text-muted/20 text-text-muted cursor-not-allowed'
                  : tempConfig.graphify_health.is_stale
                    ? 'bg-warning/20 border-warning/30 hover:bg-warning/30 text-warning'
                    : 'bg-success/10 border-success/20 hover:bg-success/20 text-success'
              }`}
            >
              <RefreshCw size={12} className={rebuilding ? "animate-spin" : ""} />
              {rebuilding ? 'Rebuilding...' : 'Rebuild Graph'}
            </button>
          )}
        </div>
      )}

      {/* Target status cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 animate-fade-up stagger-1">
        {Object.entries(CLI_CONFIGS).map(([cid, info]) => {
          const tempVal = tempConfig.targets[cid];
          return (
            <div key={cid} className={`group relative rounded-lg p-5 overflow-hidden transition-all duration-300 hover-lift ${
              tempVal
                ? 'glass-gold'
                : 'glass opacity-60'
            }`}>
              {/* Gold accent line */}
              {tempVal && (
                <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-accent/40 to-transparent" />
              )}
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15]">Target</span>
                <span className={`h-2 w-2 rounded-full ${tempVal ? 'bg-success shadow-[0_0_8px_rgba(52,211,153,0.4)] animate-pulse' : 'bg-text-muted/30'}`} />
              </div>
              <h3 className="text-[15px] font-medium text-text-primary flex items-center gap-2.5">
                {cid === 'claude' && <MessageSquareCode className="h-4 w-4 text-info" />}
                {cid === 'codex' && <TerminalIcon className="h-4 w-4 text-success" />}
                {cid === 'agy' && <Sparkles className="h-4 w-4 text-accent" />}
                {info.name}
              </h3>
              <p className="text-[11px] text-text-muted mt-2 leading-relaxed">
                {tempVal ? "Staged to sync templates on install" : "Excluded from install"}
              </p>
            </div>
          );
        })}
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 animate-fade-up stagger-2">
        <div
          onClick={() => { setExplorerFilter('agents'); setActiveTab('explorer'); }}
          className="glass rounded-lg p-4 flex items-center gap-4 cursor-pointer hover-lift group"
        >
          <div className="h-10 w-10 rounded-lg bg-info-dim border border-info/15 flex items-center justify-center group-hover:border-info/30 transition-colors">
            <Bot className="h-5 w-5 text-info" />
          </div>
          <div>
            <div className="text-[10px] text-text-muted uppercase font-semibold tracking-[0.12]">Agents</div>
            <div className="text-xl font-display text-text-primary">{tempConfig.agents.length}</div>
          </div>
        </div>

        <div
          onClick={() => { setExplorerFilter('skills'); setActiveTab('explorer'); }}
          className="glass rounded-lg p-4 flex items-center gap-4 cursor-pointer hover-lift group"
        >
          <div className="h-10 w-10 rounded-lg bg-accent-dim border border-accent/15 flex items-center justify-center group-hover:border-accent/30 transition-colors">
            <Wrench className="h-5 w-5 text-accent" />
          </div>
          <div>
            <div className="text-[10px] text-text-muted uppercase font-semibold tracking-[0.12]">Skills</div>
            <div className="text-xl font-display text-text-primary">{tempConfig.skills.length}</div>
          </div>
        </div>

        <div
          onClick={() => setActiveTab('mcp')}
          className="glass rounded-lg p-4 flex items-center gap-4 cursor-pointer hover-lift group col-span-2"
        >
          <div className="h-10 w-10 rounded-lg bg-accent-dim border border-accent-glow flex items-center justify-center group-hover:border-accent-dim transition-colors">
            <Cpu className="h-5 w-5 text-accent" />
          </div>
          <div className="flex-1">
            <div className="text-[10px] text-text-muted uppercase font-semibold tracking-[0.12]">MCP Servers</div>
            <div className="text-[13px] font-medium text-text-primary mt-0.5">
              <span className="text-success">{tempConfig.all_mcp.length - tempConfig.disabled_mcp.length} Active</span>
              <span className="text-text-muted mx-1.5">|</span>
              <span className="text-text-muted">{tempConfig.disabled_mcp.length} Disabled</span>
            </div>
          </div>
        </div>
      </div>

      {/* Agents & Skills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-up stagger-3">
        {/* Agents */}
        <div className="glass rounded-lg p-5 flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.08]">
            <h4 className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.12] flex items-center gap-2">
              <Bot className="h-3.5 w-3.5 text-info" /> Agents ({tempConfig.agents.length})
            </h4>
            <button
              onClick={() => { setExplorerFilter('agents'); setActiveTab('explorer'); }}
              className="text-[10px] text-info hover:opacity-80 font-medium transition-colors cursor-pointer"
            >
              View All →
            </button>
          </div>
          <div className="flex flex-col gap-1.5 max-h-[180px] overflow-y-auto">
            {tempConfig.agents.slice(0, 3).map(agentName => (
              <div
                key={agentName}
                onClick={() => { setSelectedExplorer({ type: 'agent', name: agentName }); setActiveTab('explorer'); }}
                className="flex items-center justify-between p-2.5 bg-white/[0.04] border border-white/[0.08] hover:border-info/30 rounded-lg cursor-pointer transition-all duration-200"
              >
                <span className="text-sm font-mono text-text-primary font-medium">{agentName}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-info-dim text-info border border-info/15 font-medium">Agent</span>
              </div>
            ))}
            {tempConfig.agents.length === 0 && (
              <div className="text-[11px] text-text-muted text-center py-4">No agents configured</div>
            )}
          </div>
        </div>

        {/* Skills */}
        <div className="glass rounded-lg p-5 flex flex-col">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-white/[0.08]">
            <h4 className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.12] flex items-center gap-2">
              <Wrench className="h-3.5 w-3.5 text-accent" /> Skills ({tempConfig.skills.length})
            </h4>
            <button
              onClick={() => { setExplorerFilter('skills'); setActiveTab('explorer'); }}
              className="text-[10px] text-accent hover:opacity-80 font-medium transition-colors cursor-pointer"
            >
              View All →
            </button>
          </div>
          <div className="flex flex-col gap-1.5 max-h-[180px] overflow-y-auto">
            {tempConfig.skills.slice(0, 3).map(skillName => (
              <div
                key={skillName}
                onClick={() => { setSelectedExplorer({ type: 'skill', name: skillName }); setActiveTab('explorer'); }}
                className="flex items-center justify-between p-2.5 bg-white/[0.04] border border-white/[0.08] hover:border-accent/30 rounded-lg cursor-pointer transition-all duration-200"
              >
                <span className="text-sm font-mono text-text-primary font-medium">{skillName}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-dim text-accent border border-accent/15 font-medium">Skill</span>
              </div>
            ))}
            {tempConfig.skills.length === 0 && (
              <div className="text-[11px] text-text-muted text-center py-4">No skills configured</div>
            )}
          </div>
        </div>
      </div>

      {/* Logs terminal */}
      <div className="glass rounded-lg overflow-hidden flex flex-col flex-1 min-h-[350px] animate-fade-up stagger-4">
        <div className="border-b border-white/[0.08] px-5 py-3 flex items-center justify-between bg-white/[0.03]">
          <div className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.12] flex items-center gap-2">
            <TerminalIcon className="h-3.5 w-3.5 text-accent/50" /> Process Output
          </div>
          <button
            onClick={() => setLogs([])}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-white/[0.03] border border-white/[0.10] hover:border-error/20 hover:text-error text-[10px] font-medium text-text-muted rounded-md cursor-pointer transition-all duration-200"
          >
            <Trash className="h-3 w-3" /> Clear
          </button>
        </div>
        <div ref={logContainerRef} className="flex-1 bg-bg p-5 font-mono text-[12px] leading-relaxed text-text-secondary overflow-y-auto max-h-[400px]">
          {logs.length > 0 ? (
            logs.map((log, index) => (
              <div key={index} className="mb-0.5">
                {ansiToHtml(log)}
              </div>
            ))
          ) : (
            <div className="text-text-muted/70 text-center py-8">
              <TerminalIcon className="h-6 w-6 mx-auto mb-2 opacity-30" />
              <p>No logs yet. Apply changes to see output.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
