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

export function getToolLabel(step: ConversationStep): string {
  const type = step.type;
  const args = step.resolved_args;

  switch (type) {
    case 'RUN_COMMAND': {
      const cmd = args?.CommandLine || args?.commandLine || args?.command || args?.script || args?.cmd || '';
      return cmd ? `Shell: ${truncate(cmd, 60)}` : 'Shell';
    }
    case 'VIEW_FILE': {
      const fp = args?.AbsolutePath || args?.absolutePath || args?.file_path || args?.path || args?.filePath || '';
      return fp ? `View: ${basename(fp)}` : 'View';
    }
    case 'CODE_ACTION': {
      const fp = args?.TargetFile || args?.targetFile || args?.file_path || args?.path || args?.filePath || args?.filename || '';
      return fp ? `Edit: ${basename(fp)}` : 'Edit';
    }
    case 'GREP_SEARCH': {
      const pattern = args?.Query || args?.query || args?.pattern || args?.regex || args?.search || '';
      return pattern ? `Grep: ${truncate(pattern, 40)}` : 'Grep';
    }
    case 'LIST_DIRECTORY': {
      const dir = args?.DirectoryPath || args?.directoryPath || args?.directory || args?.path || args?.dir || '';
      return dir ? `List: ${basename(dir)}` : 'List';
    }
    case 'MCP_TOOL': {
      const name = step.name || args?.ToolName || args?.toolName || args?.name || args?.tool_name || args?.tool || args?.server || '';
      return name ? `MCP: ${truncate(name, 40)}` : 'MCP';
    }
    case 'INVOKE_SUBAGENT': {
      let name = '';
      if (args?.agent_name || args?.name || args?.agent) {
        name = args.agent_name || args.name || args.agent;
      } else if (args?.Subagents && Array.isArray(args.Subagents)) {
        name = args.Subagents.map((s: any) => s.Role || s.TypeName || '').filter(Boolean).join(', ');
      } else if (args?.TypeName) {
        name = args.Role || args.TypeName;
      }
      return name ? `Agent: ${truncate(name, 40)}` : 'Agent';
    }
    case 'SEARCH_WEB':
    case 'READ_URL_CONTENT': {
      const q = args?.query || args?.Query || args?.url || args?.Url || args?.search || '';
      return q ? `Web: ${truncate(q, 45)}` : 'Web';
    }
    case 'ASK_QUESTION': {
      const q = args?.question || args?.prompt || '';
      return q ? `Ask: ${truncate(q, 40)}` : 'Ask';
    }
    case 'CHECKPOINT': return 'Checkpoint';
    case 'ERROR_MESSAGE': return 'Error';
    case 'LIST_RESOURCES': return 'Resources';
    case 'GENERIC': return 'Action';
    default: return type;
  }
}

function getToolColor(type: string): string {
  if (type === 'RUN_COMMAND') return 'text-info bg-info-dim';
  if (type === 'VIEW_FILE' || type === 'LIST_DIRECTORY') return 'text-accent bg-accent-dim';
  if (type === 'GREP_SEARCH') return 'text-warning bg-warning-dim';
  if (type === 'ERROR_MESSAGE') return 'text-error bg-error-dim';
  return 'text-text-muted bg-white/[0.03]';
}

function truncate(str: string, max: number): string {
  if (!str) return '';
  const clean = str.replace(/[\n\r]+/g, ' ').trim();
  return clean.length > max ? clean.slice(0, max) + '...' : clean;
}

function basename(path: string): string {
  if (!path) return '';
  if (path === '/') return '/';
  const parts = path.replace(/\/$/, '').split('/');
  return parts[parts.length - 1] || path;
}


function renderMarkdown(text: string): string {
  try { return marked.parse(text) as string; } catch { return `<pre>${text}</pre>`; }
}

function renderStepContent(step: ConversationStep) {
  const content = step.content || '';
  if (!content.trim()) return null;

  const type = step.type;
  
  // These tools return plain text (code, command output, search matches, etc.)
  const isPlainText = [
    'RUN_COMMAND', 
    'VIEW_FILE', 
    'CODE_ACTION', 
    'GREP_SEARCH', 
    'LIST_DIRECTORY', 
    'ERROR_MESSAGE'
  ].includes(type);

  if (isPlainText) {
    return (
      <div className="mt-2.5">
        <div className="text-[10px] text-text-muted/60 uppercase tracking-wider mb-1.5 font-semibold">Output</div>
        <div className="bg-black/40 rounded-xl border border-white/[0.08] p-4 overflow-x-auto max-h-[350px] overflow-y-auto shadow-inner scrollbar-thin">
          <pre className="text-[11px] font-mono text-text-secondary leading-relaxed whitespace-pre select-text">
            {content}
          </pre>
        </div>
      </div>
    );
  }

  // Otherwise, render as markdown
  return (
    <div className="mt-2.5">
      <div className="text-[10px] text-text-muted/60 uppercase tracking-wider mb-1.5 font-semibold">Result</div>
      <div 
        className="cv-ws-md text-xs leading-relaxed text-text-secondary font-mono bg-bg/50 rounded-xl p-4 border border-white/[0.10] max-h-[350px] overflow-y-auto shadow-inner scrollbar-thin" 
        dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} 
      />
    </div>
  );
}

function ToolCard({ step, inputRate }: { step: ConversationStep; inputRate: number }) {
  const [expanded, setExpanded] = useState(false);
  const cost = (step.est_tokens / 1000000.0) * inputRate;
  const reason = step.reason ? truncate(step.reason, 120) : '';

  return (
    <div className={`border rounded-xl overflow-hidden transition-all duration-200 shrink-0 ${
      expanded
        ? 'border-accent/20 bg-accent/[0.03] shadow-[0_0_8px_rgba(201,165,92,0.05)]'
        : 'border-white/[0.08] bg-white/[0.03] hover:border-white/[0.12]'
    }`}>
      <div onClick={() => setExpanded(!expanded)} className="flex items-center gap-3 px-4 py-3 cursor-pointer group">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${getToolColor(step.type)}`}>
          {getToolIcon(step.type)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-semibold text-text-primary truncate" title={getToolLabel(step)}>
              {getToolLabel(step)}
            </span>
          </div>
          {reason && (
            <div className="text-[10.5px] text-accent/80 mt-1 leading-normal whitespace-pre-wrap break-words" title={step.reason}>
              {reason}
            </div>
          )}
          {step.status === 'ERROR' && (
            <div className="text-[10px] text-error font-semibold mt-0.5">ERROR</div>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted font-mono">
          <span>{step.est_tokens ? `~${step.est_tokens.toLocaleString()}` : ''}</span>
          <span className="text-accent font-semibold">{formatCost(cost)}</span>
          {expanded
            ? <ChevronDown size={14} className="text-text-muted" />
            : <ChevronRight size={14} className="text-text-muted group-hover:text-text-secondary transition-colors" />
          }
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4 pt-0 animate-fade-in space-y-3">
          {step.reason && (
            <div className="text-[11px] text-accent/80 font-mono bg-accent/[0.04] rounded-lg p-3 border border-accent/10">
              <div className="text-[10px] text-accent/50 uppercase tracking-wider mb-1.5 font-semibold">Reason</div>
              <div className="whitespace-pre-wrap break-words leading-relaxed">{step.reason}</div>
            </div>
          )}
          {step.resolved_args && Object.keys(step.resolved_args).length > 0 && (
            <div className="text-[11px] text-text-muted font-mono bg-white/[0.03] rounded-lg p-3 border border-white/[0.06]">
              <div className="text-[10px] text-text-muted/60 uppercase tracking-wider mb-1.5 font-semibold">Arguments</div>
              <pre className="whitespace-pre-wrap break-all text-text-secondary select-text scrollbar-thin max-h-[150px] overflow-y-auto">{JSON.stringify(step.resolved_args, null, 2)}</pre>
            </div>
          )}
          {renderStepContent(step)}
        </div>
      )}
    </div>
  );
}

function MiniStat({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="bg-white/[0.05] border border-white/[0.08] rounded-xl px-3 py-3 text-center hover:border-accent/20 transition-colors">
      <div className="text-[10px] text-text-muted uppercase tracking-[0.12] mb-1.5 flex items-center justify-center gap-1 font-semibold">
        {icon} {label}
      </div>
      <div className="font-mono text-sm font-bold text-text-primary">{value}</div>
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
  const turnReason = turn.agent?.content?.trim() || '';

  return (
    <div className="w-[400px] border-l border-white/[0.08] bg-white/[0.03] flex flex-col flex-shrink-0">
      <div className="px-5 py-5 border-b border-white/[0.08]">
        <div className="font-display font-semibold text-base text-text-primary mb-2 flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
            <Zap size={13} className="text-accent" />
          </div>
          Tool Flow
        </div>
        {turnReason && (
          <div className="text-[11px] text-accent/80 mb-3 leading-relaxed bg-accent/[0.03] rounded-lg p-3 border border-accent/10 max-h-[120px] overflow-y-auto scrollbar-thin">
            <div className="text-[10px] text-accent/50 uppercase tracking-wider mb-1 font-semibold">AI Reasoning</div>
            <div className="cv-ws-md whitespace-pre-wrap break-words" dangerouslySetInnerHTML={{ __html: renderMarkdown(turnReason) }} />
          </div>
        )}
        <div className="text-xs text-text-muted mb-4 font-mono bg-white/[0.04] px-2 py-1 rounded inline-block">
          {turn.tools.length} calls · {stats.model_name}
        </div>
        <div className="grid grid-cols-3 gap-2">
          <MiniStat label="Input" value={formatTokens(turnInputTokens)} />
          <MiniStat label="Output" value={formatTokens(turnOutputTokens)} />
          <MiniStat label="Cost" value={formatCost(turnCost)} icon={<DollarSign size={10} />} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-1.5 scrollbar-thin">
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
        
        .scrollbar-thin::-webkit-scrollbar { width: 6px; height: 6px; }
        .scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
        .scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
        .scrollbar-thin::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>
    </div>
  );
}
