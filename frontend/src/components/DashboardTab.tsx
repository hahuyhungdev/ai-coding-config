import React, { useRef, useEffect } from 'react';
import type { FullConfig } from '../types';
import { 
  MessageSquareCode, Terminal as TerminalIcon, Sparkles, 
  Bot, Wrench, Cpu, Trash
} from 'lucide-react';

interface DashboardTabProps {
  tempConfig: FullConfig;
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
  setActiveTab: (tab: string) => void;
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
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
  setSelectedExplorer
}) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // ANSI to HTML/Tailwind parser for logs
  const ansiToHtml = (text: string) => {
    const ansiMap: Record<string, string> = {
      '31': 'text-red font-bold',
      '32': 'text-green font-bold',
      '33': 'text-peach font-bold',
      '34': 'text-blue font-bold',
      '35': 'text-mauve font-bold',
      '36': 'text-sky font-bold',
      '90': 'text-overlay1',
      '91': 'text-red',
      '92': 'text-green',
      '93': 'text-peach',
      '94': 'text-blue',
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
    <div className="flex flex-col gap-6 max-w-[900px]">
      {/* Targets statuses */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.entries(CLI_CONFIGS).map(([cid, info]) => {
          const tempVal = tempConfig.targets[cid];
          return (
            <div key={cid} className="bg-mantle border border-surface0 rounded-xl p-5 shadow-sm relative overflow-hidden flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-overlay2 uppercase tracking-wider">Target Status</span>
                <span className={`h-2.5 w-2.5 rounded-full ${tempVal ? 'bg-green animate-pulse' : 'bg-overlay0'}`} />
              </div>
              <h3 className="text-base font-bold font-display flex items-center gap-2 mt-1">
                {cid === 'claude' && <MessageSquareCode className="h-5 w-5 text-blue" />}
                {cid === 'codex' && <TerminalIcon className="h-5 w-5 text-mauve" />}
                {cid === 'agy' && <Sparkles className="h-5 w-5 text-peach" />}
                {info.name}
              </h3>
              <p className="text-xs text-subtext0 leading-normal">
                {tempVal ? "Staged to sync and refresh templates on install." : "Excluded. Configuration files will remain untouched."}
              </p>
            </div>
          );
        })}
      </div>

      {/* Stats overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div 
          onClick={() => {
            setExplorerFilter('agents');
            setActiveTab('explorer');
          }}
          className="bg-mantle border border-surface0 hover:border-blue/50 rounded-xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-200"
        >
          <div className="h-10 w-10 bg-blue/10 rounded-lg flex items-center justify-center">
            <Bot className="h-5 w-5 text-blue" />
          </div>
          <div>
            <div className="text-[10px] text-overlay1 uppercase font-bold tracking-wider">Custom Agents</div>
            <div className="text-xl font-bold font-display text-text">{tempConfig.agents.length}</div>
          </div>
        </div>

        <div 
          onClick={() => {
            setExplorerFilter('skills');
            setActiveTab('explorer');
          }}
          className="bg-mantle border border-surface0 hover:border-mauve/50 rounded-xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-200"
        >
          <div className="h-10 w-10 bg-mauve/10 rounded-lg flex items-center justify-center">
            <Wrench className="h-5 w-5 text-mauve" />
          </div>
          <div>
            <div className="text-[10px] text-overlay1 uppercase font-bold tracking-wider">Reusable Skills</div>
            <div className="text-xl font-bold font-display text-text">{tempConfig.skills.length}</div>
          </div>
        </div>

        <div 
          onClick={() => setActiveTab('mcp')}
          className="bg-mantle border border-surface0 hover:border-peach/50 rounded-xl p-4 shadow-sm flex items-center gap-4 cursor-pointer transition-all duration-200 col-span-2"
        >
          <div className="h-10 w-10 bg-peach/10 rounded-lg flex items-center justify-center">
            <Cpu className="h-5 w-5 text-peach" />
          </div>
          <div className="flex-1">
            <div className="text-[10px] text-overlay1 uppercase font-bold tracking-wider">MCP Configurations</div>
            <div className="text-xs font-semibold text-text mt-0.5">
              {tempConfig.all_mcp.length - tempConfig.disabled_mcp.length} Active / {tempConfig.disabled_mcp.length} Disabled
            </div>
          </div>
        </div>
      </div>

      {/* Custom Agents & Reusable Skills library overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Agents list */}
        <div className="bg-mantle border border-surface0 rounded-xl p-5 flex flex-col gap-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-surface0 pb-2.5">
            <h4 className="text-xs font-bold text-overlay2 uppercase tracking-wider flex items-center gap-1.5 font-display">
              <Bot className="h-4 w-4 text-blue" /> Custom Agents ({tempConfig.agents.length})
            </h4>
            <button 
              onClick={() => {
                setExplorerFilter('agents');
                setActiveTab('explorer');
              }}
              className="text-[10px] text-blue hover:underline font-bold transition-all cursor-pointer"
            >
              View All
            </button>
          </div>
          <div className="flex flex-col gap-2 max-h-[180px] overflow-y-auto pr-1">
            {tempConfig.agents.slice(0, 3).map(agentName => (
              <div 
                key={agentName}
                onClick={() => {
                  setSelectedExplorer({ type: 'agent', name: agentName });
                  setActiveTab('explorer');
                }}
                className="flex items-center justify-between p-2.5 bg-crust border border-surface1 hover:border-blue/30 rounded-lg cursor-pointer transition-all duration-150"
              >
                <span className="text-xs font-mono font-bold text-subtext1">{agentName}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue/10 text-blue border border-blue/20">Agent</span>
              </div>
            ))}
            {tempConfig.agents.length === 0 && (
              <div className="text-xs text-overlay1 text-center py-4">No agents found</div>
            )}
          </div>
        </div>

        {/* Skills list */}
        <div className="bg-mantle border border-surface0 rounded-xl p-5 flex flex-col gap-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-surface0 pb-2.5">
            <h4 className="text-xs font-bold text-overlay2 uppercase tracking-wider flex items-center gap-1.5 font-display">
              <Wrench className="h-4 w-4 text-mauve" /> Reusable Skills ({tempConfig.skills.length})
            </h4>
            <button 
              onClick={() => {
                setExplorerFilter('skills');
                setActiveTab('explorer');
              }}
              className="text-[10px] text-mauve hover:underline font-bold transition-all cursor-pointer"
            >
              View All
            </button>
          </div>
          <div className="flex flex-col gap-2 max-h-[180px] overflow-y-auto pr-1">
            {tempConfig.skills.slice(0, 3).map(skillName => (
              <div 
                key={skillName}
                onClick={() => {
                  setSelectedExplorer({ type: 'skill', name: skillName });
                  setActiveTab('explorer');
                }}
                className="flex items-center justify-between p-2.5 bg-crust border border-surface1 hover:border-mauve/30 rounded-lg cursor-pointer transition-all duration-150"
              >
                <span className="text-xs font-mono font-bold text-subtext1">{skillName}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-mauve/10 text-mauve border border-mauve/20">Skill</span>
              </div>
            ))}
            {tempConfig.skills.length === 0 && (
              <div className="text-xs text-overlay1 text-center py-4">No skills found</div>
            )}
          </div>
        </div>
      </div>

      {/* Logs output */}
      <div className="bg-crust border border-surface0 rounded-xl overflow-hidden shadow-lg flex flex-col flex-1 min-h-[350px]">
        <div className="bg-mantle border-b border-surface0 px-5 py-3 flex items-center justify-between">
          <div className="text-xs font-bold text-overlay2 font-display uppercase tracking-wider flex items-center gap-2">
            <TerminalIcon className="h-3.5 w-3.5 text-overlay2" /> Process Output Logs
          </div>
          <button 
            onClick={() => setLogs([])}
            className="flex items-center gap-1 px-2 py-1 bg-surface0 border border-surface1 hover:border-surface2 text-[10px] font-bold rounded cursor-pointer transition-all"
          >
            <Trash className="h-3 w-3" /> Clear Logs
          </button>
        </div>
        <div className="flex-1 bg-[#12131e] p-5 font-mono text-[13px] leading-relaxed text-gray-300 overflow-y-auto max-h-[400px]">
          {logs.length > 0 ? (
            logs.map((log, index) => (
              <div key={index} className="mb-1">
                {ansiToHtml(log)}
              </div>
            ))
          ) : (
            <div className="text-overlay2">No logs written. Apply changes to inspect script runs.</div>
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
};
