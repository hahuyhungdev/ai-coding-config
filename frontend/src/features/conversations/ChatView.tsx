import { useEffect, useRef } from 'react';
import { marked } from 'marked';
import { User, Bot } from 'lucide-react';
import type { ConversationTurn } from '../../types';

marked.setOptions({ breaks: true, gfm: true });

function renderMarkdown(text: string): string {
  try { return marked.parse(text) as string; } catch { return `<pre>${text}</pre>`; }
}

interface ChatViewProps {
  turn: ConversationTurn | null;
  onToggleWorkspace?: () => void;
  isWorkspaceOpen?: boolean;
}

export function ChatView({ turn, onToggleWorkspace, isWorkspaceOpen }: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [turn?.index]);

  if (!turn) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-text-muted">
        No turn data available
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto p-6 flex flex-col gap-5">
      {/* User Message */}
      {turn.user && (
        <div className="flex gap-3 max-w-[85%] animate-fade-in">
          <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/20 flex items-center justify-center flex-shrink-0">
            <User size={14} className="text-accent" />
          </div>
          <div className="bg-accent/[0.04] border border-accent/10 rounded-xl rounded-tl-md px-4 py-3.5 text-sm leading-relaxed text-text-primary">
            <div className="text-[10px] font-semibold text-accent mb-2 uppercase tracking-[0.12]">You</div>
            <div className="cv-markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(turn.user.content) }} />
            <div className="mt-2.5 text-[10px] text-text-muted font-mono">~{turn.user.est_tokens.toLocaleString()} tk</div>
          </div>
        </div>
      )}

      {/* AI Response */}
      {turn.agent && (
        <div className="flex gap-3 max-w-[85%] self-end animate-fade-in">
          <div className="glass rounded-xl rounded-tr-md px-4 py-3.5 text-sm leading-relaxed text-text-primary">
            <div className="text-[10px] font-semibold text-success mb-2 uppercase tracking-[0.12]">Assistant</div>
            <div className="cv-markdown" dangerouslySetInnerHTML={{ __html: renderMarkdown(turn.agent.content) }} />
            <div className="mt-2.5 text-[10px] text-text-muted font-mono">~{turn.agent.est_tokens.toLocaleString()} tk</div>
          </div>
          <div className="w-8 h-8 rounded-lg bg-success/15 border border-success/20 flex items-center justify-center flex-shrink-0">
            <Bot size={14} className="text-success" />
          </div>
        </div>
      )}

      {/* Tool calls */}
      {turn.tools.length > 0 && (
        <button
          onClick={onToggleWorkspace}
          disabled={isWorkspaceOpen}
          className={`w-full text-left px-4 py-3 rounded-lg border transition-all duration-200 text-xs text-text-muted ${
            isWorkspaceOpen
              ? 'bg-white/[0.02] border-white/[0.05] cursor-default'
              : 'bg-accent/[0.03] border-accent/15 hover:bg-accent/[0.06] hover:border-accent/25 hover:text-text-secondary cursor-pointer flex items-center justify-between'
          }`}
        >
          <div>
            <span className="font-medium text-text-secondary">{turn.tools.length} tool calls</span>
            <span className="mx-2 text-white/10">·</span>
            <span className="font-mono text-[10px]">{turn.tools.map(t => t.type).filter((v, i, a) => a.indexOf(v) === i).join(', ')}</span>
          </div>
          {!isWorkspaceOpen && (
            <span className="text-[10px] text-accent font-semibold tracking-wide flex items-center gap-1">
              View details →
            </span>
          )}
        </button>
      )}

      <style>{`
        .cv-markdown p { margin: 0 0 10px; }
        .cv-markdown p:last-child { margin: 0; }
        .cv-markdown code {
          background: rgba(255,255,255,0.04);
          padding: 2px 6px;
          border-radius: 4px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 12px;
          color: var(--color-accent);
        }
        .cv-markdown pre {
          background: rgba(0,0,0,0.3);
          border: 1px solid rgba(255,255,255,0.04);
          border-radius: 8px;
          padding: 14px 18px;
          overflow-x: auto;
          margin: 10px 0;
        }
        .cv-markdown pre code {
          background: none;
          padding: 0;
          font-size: 12px;
          line-height: 1.6;
          color: var(--color-text-secondary);
        }
        .cv-markdown ul, .cv-markdown ol { padding-left: 20px; margin: 6px 0; }
        .cv-markdown li { margin: 3px 0; }
        .cv-markdown blockquote {
          border-left: 2px solid var(--color-accent);
          padding-left: 14px;
          margin: 10px 0;
          color: var(--color-text-muted);
          font-style: italic;
        }
        .cv-markdown h1, .cv-markdown h2, .cv-markdown h3 {
          font-family: 'Instrument Serif', serif;
          font-weight: 400;
          margin: 14px 0 6px;
          color: var(--color-text-primary);
        }
        .cv-markdown h1 { font-size: 20px; }
        .cv-markdown h2 { font-size: 17px; }
        .cv-markdown h3 { font-size: 15px; }
        .cv-markdown a { color: var(--color-accent); text-decoration: none; }
        .cv-markdown a:hover { text-decoration: underline; }
        .cv-markdown table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        .cv-markdown th, .cv-markdown td {
          border: 1px solid rgba(255,255,255,0.06);
          padding: 8px 12px;
          text-align: left;
          font-size: 13px;
        }
        .cv-markdown th { background: rgba(255,255,255,0.03); font-weight: 600; }
      `}</style>
    </div>
  );
}
