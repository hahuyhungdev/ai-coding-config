import { MessageSquare, Search, Clock, HardDrive, Zap, DollarSign } from 'lucide-react';
import { formatDate, formatBytes, formatTokens, formatCost } from '../../utils/format';
import { useConversations } from '../../hooks/useConversations';
import { ChatView } from './ChatView';
import { TokenStats } from './TokenStats';
import { WorkspaceView } from './WorkspaceView';

export function ConversationViewer() {
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
            <div className="w-7 h-7 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
              <MessageSquare size={14} className="text-accent" />
            </div>
            <span className="font-display font-semibold text-sm text-text-primary">Conversations</span>
          </div>
          <span className="text-[10px] text-text-muted font-mono bg-white/[0.03] px-2 py-0.5 rounded-md">{filteredConversations.length}</span>
        </div>

        <div className="px-4 py-3">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input type="text" placeholder="Search..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.10] rounded-lg py-2 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted/70 focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300" />
          </div>
        </div>

        <div className="flex items-center gap-2 px-5 pb-3 text-[10px] text-text-muted">
          <span>{filteredConversations.length} items</span>
          <span className="text-white/10">·</span>
          <span>{formatBytes(filteredConversations.reduce((s, c) => s + c.size_bytes, 0))}</span>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {filteredConversations.map(conv => (
            <button key={conv.id} onClick={() => selectConversation(conv.id)}
              className={`w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                activeConvId === conv.id
                  ? 'bg-accent/[0.06] border border-accent/15'
                  : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.08]'
              }`}>
              <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                  conv.source === 'claude' ? 'bg-purple-500/10 text-purple-400' :
                  conv.source === 'codex' ? 'bg-emerald-500/10 text-emerald-400' :
                  'bg-cyan-500/10 text-cyan-400'
                }`}>
                  {conv.source || 'gemini'}
                </span>
                <span className="text-[10px] text-text-muted font-medium truncate max-w-[140px]" title={conv.project}>
                  {conv.project || 'Global'}
                </span>
              </div>
              <div className="text-[13px] font-medium text-text-primary leading-snug line-clamp-2 mb-1.5 group-hover:text-accent transition-colors">
                {conv.title}
              </div>
              <div className="flex items-center gap-3 text-[10px] text-text-muted">
                <span className="flex items-center gap-1"><Clock size={10} />{formatDate(conv.last_updated)}</span>
                <span className="flex items-center gap-1"><HardDrive size={10} />{formatBytes(conv.size_bytes)}</span>
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
                <div className="font-display font-semibold text-base text-text-primary mb-0.5">
                  #{activeConvId?.slice(0, 8)}
                </div>
                <div className="text-xs text-text-muted font-mono">{activeConvData.stats.model_name}</div>
              </div>
              <div className="flex gap-2">
                <TokenStats icon={<Zap size={13} />} label="In" value={formatTokens(activeConvData.stats.est_input_tokens)} color="text-accent" />
                <TokenStats icon={<Zap size={13} />} label="Out" value={formatTokens(activeConvData.stats.est_output_tokens)} color="text-success" />
                <TokenStats icon={<DollarSign size={13} />} label="Cost" value={formatCost(activeConvData.stats.est_cost)} color="text-warning" />
              </div>
            </div>

            {turns.length > 0 && (
              <div className="flex items-center gap-1 px-6 py-2 border-b border-white/[0.08] bg-white/[0.03] overflow-x-auto">
                {turns.map((turn, i) => (
                  <button key={i} onClick={() => setActiveTurn(i)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono whitespace-nowrap transition-all duration-200 ${
                      activeTurn === i
                        ? 'bg-accent/90 text-bg shadow-[0_0_10px_rgba(201,165,92,0.15)]'
                        : 'text-text-muted hover:text-text-secondary hover:bg-white/[0.03]'
                    }`}>
                    Turn {i + 1}
                    {turn.tools.length > 0 && <span className="ml-1 opacity-50">({turn.tools.length})</span>}
                  </button>
                ))}
              </div>
            )}

            <div className="flex-1 flex overflow-hidden">
              <div className="flex-1 overflow-hidden"><ChatView turn={currentTurn} /></div>
              {currentTurn && currentTurn.tools.length > 0 && <WorkspaceView turn={currentTurn} stats={activeConvData.stats} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
