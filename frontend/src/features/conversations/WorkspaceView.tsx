import { useState } from 'react';
import { marked } from 'marked';
import {
  Terminal, FileText, Search, FolderOpen, Globe, Code,
  ChevronDown, ChevronRight, Zap, DollarSign
} from 'lucide-react';
import type { ConversationTurn, ConversationStats, ConversationStep } from '../../types';
import { formatTokens, formatCost } from '../../utils/format';

function getToolIcon(type: string) {
  const iconClass = "w-3.5 h-3.5";
  switch (type) {
    case 'RUN_COMMAND': return <Terminal className={iconClass} />;
    case 'VIEW_FILE': return <FileText className={iconClass} />;
    case 'GREP_SEARCH': return <Search className={iconClass} />;
    case 'LIST_DIRECTORY': return <FolderOpen className={iconClass} />;
    case 'SEARCH_WEB':
    case 'READ_URL_CONTENT': return <Globe className={iconClass} />;
    case 'CODE_ACTION': return <Code className={iconClass} />;
    default: return <Code className={iconClass} />;
  }
}

function getToolLabel(type: string): string {
  const labels: Record<string, string> = {
    RUN_COMMAND: 'Shell', VIEW_FILE: 'View', GREP_SEARCH: 'Search',
    LIST_DIRECTORY: 'List', MCP_TOOL: 'MCP', CODE_ACTION: 'Code',
    SEARCH_WEB: 'Web', READ_URL_CONTENT: 'URL', ASK_QUESTION: 'Ask',
    INVOKE_SUBAGENT: 'Agent', CHECKPOINT: 'Checkpoint', ERROR_MESSAGE: 'Error',
    LIST_RESOURCES: 'Resources', GENERIC: 'Action',
  };
  return labels[type] || type;
}

function getToolColor(type: string): string {
  if (type === 'RUN_COMMAND') return 'text-info bg-info-dim';
  if (type === 'VIEW_FILE' || type === 'LIST_DIRECTORY') return 'text-accent bg-accent-dim';
  if (type === 'GREP_SEARCH') return 'text-warning bg-warning-dim';
  if (type === 'ERROR_MESSAGE') return 'text-error bg-error-dim';
  return 'text-text-muted bg-white/[0.03]';
}

function renderMarkdown(text: string): string {
  try { return marked.parse(text) as string; } catch { return `<pre>${text}</pre>`; }
}

function ToolCard({ step, inputRate }: { step: ConversationStep; inputRate: number }) {
  const [expanded, setExpanded] = useState(false);
  const cost = (step.est_tokens / 1000000.0) * inputRate;

  return (
    <div className="border border-white/[0.08] rounded-lg overflow-hidden bg-white/[0.03] transition-all duration-200 hover:border-white/[0.08] shrink-0">
      <div onClick={() => setExpanded(!expanded)} className="flex items-center gap-2.5 px-3 py-2.5 cursor-pointer group">
        <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${getToolColor(step.type)}`}>
          {getToolIcon(step.type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-text-primary truncate">{getToolLabel(step.type)}</div>
        </div>
        <div className="flex items-center gap-2.5 text-[10px] text-text-muted font-mono">
          <span>~{step.est_tokens.toLocaleString()}</span>
          <span className="text-accent">{formatCost(cost)}</span>
          {expanded
            ? <ChevronDown size={12} className="text-text-muted" />
            : <ChevronRight size={12} className="text-text-muted group-hover:text-text-secondary transition-colors" />
          }
        </div>
      </div>
      {expanded && (
        <div className="px-3 pb-3 pt-0 animate-fade-in">
          <div className="cv-ws-md text-[11px] leading-relaxed text-text-secondary font-mono bg-bg/50 rounded-md p-3 border border-white/[0.10]" dangerouslySetInnerHTML={{ __html: renderMarkdown(step.content) }} />
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2.5 text-center hover:border-white/[0.08] transition-colors">
      <div className="text-[9px] text-text-muted uppercase tracking-[0.12] mb-1 flex items-center justify-center gap-1 font-semibold">
        {icon} {label}
      </div>
      <div className="font-mono text-sm font-semibold text-text-primary">{value}</div>
    </div>
  );
}

interface WorkspaceViewProps {
  turn: ConversationTurn;
  stats: ConversationStats;
}

export function WorkspaceView({ turn, stats }: WorkspaceViewProps) {
  const turnOutputTokens = turn.agent?.est_tokens || 0;
  const turnToolsTokens = turn.tools.reduce((s, t) => s + t.est_tokens, 0);
  const turnUserTokens = turn.user?.est_tokens || 0;
  const turnInputTokens = 25000 + turnUserTokens + turnToolsTokens;
  const turnCost = (turnInputTokens / 1000000.0 * stats.input_rate) + (turnOutputTokens / 1000000.0 * stats.output_rate);

  return (
    <div className="w-[380px] border-l border-white/[0.08] bg-white/[0.03] flex flex-col flex-shrink-0">
      <div className="px-4 py-4 border-b border-white/[0.08]">
        <div className="font-display font-semibold text-sm text-text-primary mb-2 flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-accent/10 border border-accent/15 flex items-center justify-center">
            <Zap size={12} className="text-accent" />
          </div>
          Tool Flow
        </div>
        <div className="text-[10px] text-text-muted mb-3 font-mono">
          {turn.tools.length} calls · {stats.model_name}
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          <MiniStat label="In" value={formatTokens(turnInputTokens)} />
          <MiniStat label="Out" value={formatTokens(turnOutputTokens)} />
          <MiniStat label="Cost" value={formatCost(turnCost)} icon={<DollarSign size={9} />} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-1">
        {turn.tools.map((step, i) => (
          <ToolCard key={i} step={step} inputRate={stats.input_rate} />
        ))}
      </div>

      <style>{`
        .cv-ws-md p { margin: 0 0 6px; }
        .cv-ws-md p:last-child { margin: 0; }
        .cv-ws-md pre { background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.04); border-radius: 6px; padding: 10px 14px; overflow-x: auto; margin: 6px 0; font-size: 11px; line-height: 1.5; }
        .cv-ws-md code { background: rgba(255,255,255,0.04); padding: 1px 4px; border-radius: 3px; font-size: 11px; color: var(--color-accent); }
        .cv-ws-md pre code { background: none; padding: 0; color: var(--color-text-secondary); }
        .cv-ws-md ul, .cv-ws-md ol { padding-left: 16px; margin: 4px 0; }
        .cv-ws-md li { margin: 2px 0; }
      `}</style>
    </div>
  );
}
