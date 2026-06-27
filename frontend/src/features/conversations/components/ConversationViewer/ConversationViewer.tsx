import { useState } from 'react';
import { MessageSquare, Search, Clock, HardDrive, Zap, DollarSign, Terminal, ChevronLeft, ChevronRight, BarChart2 } from 'lucide-react';
import { formatDate, formatBytes, formatTokens, formatCost } from '../../../../utils/format';
import { useConversations } from '../../hooks/useConversations';
import { ChatView } from '../ChatView/ChatView';
import { TokenStats } from '../TokenStats/TokenStats';
import { WorkspaceView } from '../WorkspaceView/WorkspaceView';
interface ConversationViewerProps {
  fallback?: React.ReactNode;
}

export function ConversationViewer({ fallback }: ConversationViewerProps) {
  const [showWorkspace, setShowWorkspace] = useState(true);
  const {
    filteredConversations, activeConvId, activeConvData,
    activeTurn, setActiveTurn, searchQuery, setSearchQuery,
    isLoading, selectConversation, deselectConversation, turns, currentTurn
  } = useConversations();

  return (
    <div className="flex h-full overflow-hidden rounded-xl glass">
      {/* Sidebar */}
      <aside className={`w-80 flex flex-col flex-shrink-0 border-r border-white/[0.08] bg-white/[0.03] ${
        activeConvId ? 'hidden lg:flex' : 'flex'
      }`}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
              <MessageSquare size={15} className="text-accent" />
            </div>
            <div>
              <span className="font-display font-semibold text-sm text-text-primary block">Conversations</span>
              <span className="text-[13px] text-text-muted">{filteredConversations.length} items · {formatBytes(filteredConversations.reduce((s, c) => s + c.size_bytes, 0))}</span>
            </div>
          </div>
        </div>

        <div className="px-4 py-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input type="text" aria-label="Search conversations" placeholder="Search conversations..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.10] rounded-lg py-2.5 pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/10 transition-all duration-300" />
          </div>
        </div>

        <div className="px-2.5 pb-2">
          <button
            onClick={deselectConversation}
            className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl transition-all duration-200 group border ${
              activeConvId === null
                ? 'bg-accent/[0.08] border-accent/20 shadow-[0_0_12px_rgba(201,165,92,0.06)] text-accent font-semibold'
                : 'border-transparent text-text-secondary hover:bg-white/[0.04] hover:text-text-primary'
            }`}
          >
            <BarChart2 size={14} className={activeConvId === null ? 'text-accent' : 'text-text-muted group-hover:text-text-secondary'} />
            <span className="font-display text-[13px]">Analytics Dashboard</span>
          </button>
        </div>

        <div className="h-px bg-white/[0.08] mx-4 mb-2" />

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
                  conv.source === 'claude' ? 'bg-orange-500/15 text-orange-400 border border-orange-500/20' :
                  conv.source === 'codex' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' :
                  'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20'
                }`}>
                  {conv.source || 'gemini'}
                </span>
                <span className="text-[13px] text-text-secondary font-medium truncate" title={conv.project}>
                  {conv.project || 'Global'}
                </span>
              </div>
              <div className="text-[14px] font-semibold text-text-primary leading-snug line-clamp-2 mb-2 group-hover:text-accent transition-colors">
                {conv.title}
              </div>
              <div className="flex items-center gap-3 text-[13px] text-text-muted">
                <span className="flex items-center gap-1.5"><Clock size={11} className="text-accent" />{formatDate(conv.last_updated)}</span>
                <span className="flex items-center gap-1.5"><HardDrive size={11} className="text-accent" />{formatBytes(conv.size_bytes)}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="flex-1 flex flex-col overflow-hidden">
        {!activeConvId ? (
          <div className="flex-1 overflow-y-auto main-content-scrollbar p-6">
            {fallback}
          </div>
        ) : isLoading || !activeConvData ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
              Loading...
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-6 px-6 py-4 border-b border-white/[0.08] bg-white/[0.03]">
              {activeConvId && (
                <button
                  onClick={deselectConversation}
                  className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-white/[0.06] text-text-secondary hover:text-text-primary transition-colors cursor-pointer flex items-center gap-1 text-xs font-semibold"
                  title="Back to List"
                >
                  <ChevronLeft size={16} />
                  <span>List</span>
                </button>
              )}
              <div className="flex-1">
                <div className="font-display font-semibold text-lg text-text-primary mb-1">
                  #{activeConvId?.slice(0, 8)}
                </div>
                <div className="text-xs text-text-muted font-mono bg-white/[0.04] px-2 py-0.5 rounded inline-block">{activeConvData.stats.model_name}</div>
              </div>
              <div className="flex gap-3 items-center">
                {/* Compact Turn Switcher */}
                {turns.length > 0 && (
                  <div className="flex items-center bg-white/[0.03] border border-white/[0.08] rounded-lg p-1 gap-1 mr-2 shadow-inner">
                    <button
                      disabled={activeTurn === 0}
                      onClick={() => setActiveTurn(activeTurn - 1)}
                      className="p-1 rounded text-text-muted hover:text-text-primary disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition-colors"
                      title="Previous Turn"
                    >
                      <ChevronLeft size={14} />
                    </button>
                    <span className="text-[11px] font-mono font-semibold px-2 text-text-secondary select-none">
                      Turn {activeTurn + 1} / {turns.length}
                    </span>
                    <button
                      disabled={activeTurn === turns.length - 1}
                      onClick={() => setActiveTurn(activeTurn + 1)}
                      className="p-1 rounded text-text-muted hover:text-text-primary disabled:opacity-30 disabled:pointer-events-none cursor-pointer transition-colors"
                      title="Next Turn"
                    >
                      <ChevronRight size={14} />
                    </button>
                  </div>
                )}

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

            <div className="flex-1 flex overflow-hidden relative">
              <div className="flex-1 overflow-hidden">
                <ChatView
                  turn={currentTurn}
                  onToggleWorkspace={() => setShowWorkspace(true)}
                  isWorkspaceOpen={showWorkspace}
                />
              </div>
              {currentTurn && currentTurn.tools.length > 0 && showWorkspace && (
                <div className="absolute inset-y-0 right-0 z-10 md:relative md:z-0 w-full md:w-[350px] lg:w-[400px] h-full flex flex-col bg-bg md:bg-transparent">
                  <WorkspaceView
                    turn={currentTurn}
                    stats={activeConvData.stats}
                    turns={turns}
                    activeTurn={activeTurn}
                    setActiveTurn={setActiveTurn}
                    onClose={() => setShowWorkspace(false)}
                  />
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
