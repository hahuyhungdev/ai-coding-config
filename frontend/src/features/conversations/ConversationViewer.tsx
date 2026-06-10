import { useState } from 'react';
import { MessageSquare, Search, Clock, HardDrive, Zap, DollarSign, Terminal } from 'lucide-react';
import { formatDate, formatBytes, formatTokens, formatCost } from '../../utils/format';
import { useConversations } from '../../hooks/useConversations';
import { ChatView } from './ChatView';
import { TokenStats } from './TokenStats';
import { WorkspaceView } from './WorkspaceView';
import type { ConversationTurn } from '../../types';

function getTurnSummary(turn: ConversationTurn): string {
  // Show brief summary of what this turn does
  if (turn.tools.length === 0) {
    if (turn.agent?.content) {
      const text = turn.agent.content.replace(/[\n\r]+/g, ' ').trim();
      return text.length > 30 ? text.slice(0, 30) + '…' : text;
    }
    return '';
  }

  // Summarize tool types used
  const typeCounts: Record<string, number> = {};
  for (const t of turn.tools) {
    typeCounts[t.type] = (typeCounts[t.type] || 0) + 1;
  }

  const parts: string[] = [];
  const order = ['RUN_COMMAND', 'CODE_ACTION', 'VIEW_FILE', 'GREP_SEARCH', 'MCP_TOOL', 'SEARCH_WEB'];
  for (const t of order) {
    if (typeCounts[t]) {
      const label = t === 'RUN_COMMAND' ? 'cmd' : t === 'CODE_ACTION' ? 'edit' : t === 'VIEW_FILE' ? 'read' : t === 'GREP_SEARCH' ? 'grep' : t === 'MCP_TOOL' ? 'mcp' : 'web';
      parts.push(typeCounts[t] > 1 ? `${label}×${typeCounts[t]}` : label);
      delete typeCounts[t];
    }
  }
  for (const [t, count] of Object.entries(typeCounts)) {
    parts.push(count > 1 ? `${t.toLowerCase()}×${count}` : t.toLowerCase());
  }
  return parts.join(' · ');
}

export function ConversationViewer() {
  const [showWorkspace, setShowWorkspace] = useState(true);
  const {
    filteredConversations, activeConvId, activeConvData,
    activeTurn, setActiveTurn, searchQuery, setSearchQuery,
    isLoading, selectConversation, turns, currentTurn
  } = useConversations();

  return (
    <div className="flex h-full overflow-hidden rounded-xl glass">
      {/* Sidebar */}
      <aside className="w-80 flex flex-col flex-shrink-0 border-r border-white/[0.08] bg-white/[0.03]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
              <MessageSquare size={15} className="text-accent" />
            </div>
            <div>
              <span className="font-display font-semibold text-sm text-text-primary block">Conversations</span>
              <span className="text-[11px] text-text-muted">{filteredConversations.length} items · {formatBytes(filteredConversations.reduce((s, c) => s + c.size_bytes, 0))}</span>
            </div>
          </div>
        </div>

        <div className="px-4 py-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input type="text" placeholder="Search conversations..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.10] rounded-lg py-2.5 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300" />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-2.5 pb-4 space-y-1">
          {filteredConversations.map(conv => (
            <button key={conv.id} onClick={() => selectConversation(conv.id)}
              className={`w-full text-left px-3.5 py-3 rounded-xl transition-all duration-200 group ${
                activeConvId === conv.id
                  ? 'bg-accent/[0.08] border border-accent/20 shadow-[0_0_12px_rgba(201,165,92,0.06)]'
                  : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.06]'
              }`}>
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                  conv.source === 'claude' ? 'bg-purple-500/15 text-purple-400 border border-purple-500/20' :
                  conv.source === 'codex' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' :
                  'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20'
                }`}>
                  {conv.source || 'gemini'}
                </span>
                <span className="text-xs text-text-muted font-medium truncate" title={conv.project}>
                  {conv.project || 'Global'}
                </span>
              </div>
              <div className="text-[13px] font-medium text-text-primary leading-snug line-clamp-2 mb-2 group-hover:text-accent transition-colors">
                {conv.title}
              </div>
              <div className="flex items-center gap-3 text-[11px] text-text-muted">
                <span className="flex items-center gap-1.5"><Clock size={11} />{formatDate(conv.last_updated)}</span>
                <span className="flex items-center gap-1.5"><HardDrive size={11} />{formatBytes(conv.size_bytes)}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        {!activeConvData ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-text-muted">
            <div className="w-16 h-16 rounded-xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
              <MessageSquare size={28} strokeWidth={1.5} className="opacity-20" />
            </div>
            <div className="text-center">
              <div className="text-sm font-display font-semibold text-text-secondary mb-1">Select a conversation</div>
              <div className="text-xs text-text-muted">Choose from the sidebar to view details</div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
              Loading...
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-6 px-6 py-4 border-b border-white/[0.08] bg-white/[0.03]">
              <div className="flex-1">
                <div className="font-display font-semibold text-lg text-text-primary mb-1">
                  #{activeConvId?.slice(0, 8)}
                </div>
                <div className="text-xs text-text-muted font-mono bg-white/[0.04] px-2 py-0.5 rounded inline-block">{activeConvData.stats.model_name}</div>
              </div>
              <div className="flex gap-3 items-center">
                <TokenStats icon={<Zap size={14} />} label="Input" value={formatTokens(activeConvData.stats.est_input_tokens)} color="text-accent" />
                <TokenStats icon={<Zap size={14} />} label="Output" value={formatTokens(activeConvData.stats.est_output_tokens)} color="text-success" />
                <TokenStats icon={<DollarSign size={14} />} label="Cost" value={formatCost(activeConvData.stats.est_cost)} color="text-warning" />
                <button
                  onClick={() => setShowWorkspace(!showWorkspace)}
                  className={`p-2 rounded-lg border transition-all duration-200 cursor-pointer ml-2 flex items-center justify-center ${
                    showWorkspace
                      ? 'bg-accent/15 border-accent/30 text-accent shadow-[0_0_10px_rgba(201,165,92,0.15)]'
                      : 'bg-white/[0.04] border-white/[0.10] text-text-muted hover:text-text-secondary hover:bg-white/[0.06]'
                  }`}
                  title="Toggle Tool Flow"
                >
                  <Terminal size={15} />
                </button>
              </div>
            </div>

            {turns.length > 0 && (
              <div className="flex items-center gap-1.5 px-6 py-3 border-b border-white/[0.08] bg-white/[0.03] overflow-x-auto">
                {turns.map((turn, i) => {
                  const summary = getTurnSummary(turn);
                  return (
                    <button key={i} onClick={() => setActiveTurn(i)}
                      className={`px-4 py-2 rounded-lg text-xs font-mono whitespace-nowrap transition-all duration-200 ${
                        activeTurn === i
                          ? 'bg-accent text-bg font-semibold shadow-[0_0_12px_rgba(201,165,92,0.2)]'
                          : 'text-text-muted hover:text-text-secondary hover:bg-white/[0.04] border border-transparent hover:border-white/[0.06]'
                      }`}>
                      Turn {i + 1}
                      {summary && <span className="ml-1.5 opacity-60">· {summary}</span>}
                    </button>
                  );
                })}
              </div>
            )}

            <div className="flex-1 flex overflow-hidden">
              <div className="flex-1 overflow-hidden">
                <ChatView
                  turn={currentTurn}
                  onToggleWorkspace={() => setShowWorkspace(true)}
                  isWorkspaceOpen={showWorkspace}
                />
              </div>
              {currentTurn && currentTurn.tools.length > 0 && showWorkspace && <WorkspaceView turn={currentTurn} stats={activeConvData.stats} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
