import React, { useState, useEffect } from 'react';
import { Search, Bot, Wrench, Compass, Sliders } from 'lucide-react';
import { marked } from 'marked';
import type { FullConfig, ExplorerDetail } from '../../types';

interface ExplorerTabProps {
  tempConfig: FullConfig;
  selectedExplorer: { type: 'agent' | 'skill'; name: string } | null;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
  showToast: (msg: string, type: 'success' | 'error' | 'warning') => void;
  explorerFilter: 'all' | 'agents' | 'skills';
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
}

const ExplorerTab: React.FC<ExplorerTabProps> = ({
  tempConfig, selectedExplorer, setSelectedExplorer, showToast, explorerFilter, setExplorerFilter,
}) => {
  const [explorerSearch, setExplorerSearch] = useState<string>('');
  const [explorerDetail, setExplorerDetail] = useState<ExplorerDetail | null>(null);
  const [loadingExplorer, setLoadingExplorer] = useState<boolean>(false);

  useEffect(() => {
    const fetchExplorerDetail = async (type: 'agent' | 'skill', name: string) => {
      setLoadingExplorer(true);
      try {
        const res = await fetch(`/api/${type}/${name}`);
        if (!res.ok) throw new Error(`Failed to load ${type}`);
        setExplorerDetail(await res.json());
      } catch (err: any) {
        showToast(err.message, 'error');
        setExplorerDetail(null);
      } finally {
        setLoadingExplorer(false);
      }
    };
    if (selectedExplorer) fetchExplorerDetail(selectedExplorer.type, selectedExplorer.name);
    else setExplorerDetail(null);
  }, [selectedExplorer, showToast]);

  const filteredExplorerItems = [
    ...(explorerFilter === 'all' || explorerFilter === 'agents' ? tempConfig.agents.map(a => ({ type: 'agent' as const, name: a })) : []),
    ...(explorerFilter === 'all' || explorerFilter === 'skills' ? tempConfig.skills.map(s => ({ type: 'skill' as const, name: s })) : [])
  ].filter(item => item.name.toLowerCase().includes(explorerSearch.toLowerCase()));

  const accentForType = (type: 'agent' | 'skill') => type === 'agent' ? '#60a5fa' : '#c084fc';

  return (
    <div className="flex h-[calc(100vh-180px)] glass rounded-xl overflow-hidden">
      {/* Sidebar list */}
      <aside className="w-[290px] border-r border-white/[0.08] flex flex-col shrink-0 bg-white/[0.03]">
        <div className="p-4 border-b border-white/[0.08] flex flex-col gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted h-3.5 w-3.5" />
            <input type="text" placeholder="Search..." value={explorerSearch} onChange={e => setExplorerSearch(e.target.value)}
              className="w-full bg-white/[0.03] border border-white/[0.10] text-text-primary text-xs rounded-lg pl-8 pr-3 py-2 outline-none focus:border-accent/40 transition-all duration-300" />
          </div>
          <div className="grid grid-cols-3 gap-0.5 bg-white/[0.04] p-0.5 rounded-lg border border-white/[0.08]">
            {(['all', 'agents', 'skills'] as const).map(f => (
              <button key={f} onClick={() => setExplorerFilter(f)}
                className={`text-[10px] py-1 font-medium rounded cursor-pointer transition-all uppercase ${
                  explorerFilter === f ? 'bg-white/[0.06] text-text-primary' : 'text-text-muted hover:text-text-secondary'
                }`}>{f}</button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-0.5">
          {filteredExplorerItems.length > 0 ? filteredExplorerItems.map(item => {
            const selected = selectedExplorer?.type === item.type && selectedExplorer?.name === item.name;
            const Icon = item.type === 'agent' ? Bot : Wrench;
            const color = accentForType(item.type);
            return (
              <div key={`${item.type}-${item.name}`} onClick={() => setSelectedExplorer({ type: item.type, name: item.name })}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer text-xs transition-all duration-200 ${
                  selected ? `bg-white/[0.04] border-l-2` : 'hover:bg-white/[0.04] text-text-secondary border-l-2 border-transparent'
                }`} style={selected ? { borderLeftColor: color, color } : undefined}>
                <Icon className="h-4 w-4 shrink-0" style={selected ? { color } : { color: 'var(--color-text-muted)' }} />
                <div className="flex flex-col truncate">
                  <span className="font-medium truncate">{item.name}</span>
                  <span className="text-[9px] text-text-muted uppercase tracking-wide mt-0.5">{item.type}</span>
                </div>
              </div>
            );
          }) : (
            <div className="text-center text-xs text-text-muted py-8">No results</div>
          )}
        </div>
      </aside>

      {/* Detail pane */}
      <div className="flex-1 overflow-y-auto p-6">
        {loadingExplorer ? (
          <div className="h-full w-full flex items-center justify-center text-accent">
            <Sliders className="h-8 w-8 animate-spin" />
          </div>
        ) : explorerDetail ? (
          <div className="flex flex-col gap-5 max-w-[800px] animate-fade-up">
            <div className="glass rounded-xl p-6 flex flex-col gap-4 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full" style={{ backgroundColor: accentForType(selectedExplorer?.type || 'agent') }} />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {selectedExplorer?.type === 'agent' ? (
                    <div className="h-10 w-10 rounded-lg bg-[#60a5fa]/10 border border-[#60a5fa]/15 flex items-center justify-center">
                      <Bot className="h-5 w-5 text-[#60a5fa]" />
                    </div>
                  ) : (
                    <div className="h-10 w-10 rounded-lg bg-[#c084fc]/10 border border-[#c084fc]/15 flex items-center justify-center">
                      <Wrench className="h-5 w-5 text-[#c084fc]" />
                    </div>
                  )}
                  <div>
                    <h2 className="text-lg font-display text-text-primary">{explorerDetail.name}</h2>
                    <p className="text-[10px] text-text-muted uppercase tracking-[0.12] mt-0.5">
                      {selectedExplorer?.type} details
                    </p>
                  </div>
                </div>
                <span className={`text-[9px] font-mono font-semibold px-3 py-1 rounded-full uppercase border ${
                  selectedExplorer?.type === 'agent'
                    ? 'bg-[#60a5fa]/10 text-[#60a5fa] border-[#60a5fa]/15'
                    : 'bg-[#c084fc]/10 text-[#c084fc] border-[#c084fc]/15'
                }`}>{selectedExplorer?.type}</span>
              </div>

              {explorerDetail.metadata.description && (
                <p className="text-sm text-text-secondary leading-relaxed border-t border-white/[0.08] pt-3">
                  {explorerDetail.metadata.description}
                </p>
              )}

              {Object.keys(explorerDetail.metadata).filter(k => k !== 'description').length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-1 border-t border-white/[0.08] pt-3">
                  {Object.entries(explorerDetail.metadata).filter(([k]) => k !== 'description').map(([k, v]) => (
                    <span key={k} className="text-[10px] font-mono px-2 py-0.5 bg-white/[0.03] text-text-muted rounded border border-white/[0.08]">
                      {k}: {String(v)}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="glass rounded-xl p-6 flex flex-col gap-3">
              <div className="text-[10px] font-semibold text-text-muted uppercase tracking-[0.15] border-b border-white/[0.08] pb-2">
                System Prompt
              </div>
              <div
                className="prose prose-invert max-w-none text-sm text-text-secondary leading-relaxed"
                dangerouslySetInnerHTML={{ __html: marked.parse(explorerDetail.prompt) }}
              />
            </div>
          </div>
        ) : (
          <div className="h-full w-full flex flex-col items-center justify-center text-text-muted">
            <Compass className="h-12 w-12 opacity-15 mb-3 animate-pulse" />
            <span className="text-sm">Select an agent or skill to view details</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExplorerTab;
