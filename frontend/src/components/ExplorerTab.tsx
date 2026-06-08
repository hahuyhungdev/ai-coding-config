import React, { useState, useEffect } from 'react';
import { Search, Bot, Wrench, Compass, Sliders } from 'lucide-react';
import { marked } from 'marked';
import type { FullConfig, ExplorerDetail } from '../types';

interface ExplorerTabProps {
  tempConfig: FullConfig;
  selectedExplorer: { type: 'agent' | 'skill'; name: string } | null;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
  showToast: (msg: string, type: 'success' | 'error' | 'warning') => void;
  explorerFilter: 'all' | 'agents' | 'skills';
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
}

const ExplorerTab: React.FC<ExplorerTabProps> = ({
  tempConfig,
  selectedExplorer,
  setSelectedExplorer,
  showToast,
  explorerFilter,
  setExplorerFilter,
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
        const data: ExplorerDetail = await res.json();
        setExplorerDetail(data);
      } catch (err: any) {
        showToast(err.message, 'error');
        setExplorerDetail(null);
      } finally {
        setLoadingExplorer(false);
      }
    };

    if (selectedExplorer) {
      fetchExplorerDetail(selectedExplorer.type, selectedExplorer.name);
    } else {
      setExplorerDetail(null);
    }
  }, [selectedExplorer, showToast]);

  const filteredExplorerItems = [
    ...(explorerFilter === 'all' || explorerFilter === 'agents' ? tempConfig.agents.map(a => ({ type: 'agent' as const, name: a })) : []),
    ...(explorerFilter === 'all' || explorerFilter === 'skills' ? tempConfig.skills.map(s => ({ type: 'skill' as const, name: s })) : [])
  ].filter(item => item.name.toLowerCase().includes(explorerSearch.toLowerCase()));

  return (
    <div className="flex h-[calc(100vh-180px)] border border-surface0 bg-mantle rounded-xl overflow-hidden shadow-lg">
      {/* Explorer sidebar list */}
      <aside className="w-[290px] border-r border-surface0 flex flex-col shrink-0 bg-mantle">
        <div className="p-4 border-b border-surface0 flex flex-col gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-overlay1 h-3.5 w-3.5" />
            <input 
              type="text"
              placeholder="Search items..."
              value={explorerSearch}
              onChange={e => setExplorerSearch(e.target.value)}
              className="w-full bg-crust border border-surface1 text-text text-xs rounded-lg pl-8 pr-3 py-2 outline-none focus:border-blue transition-all"
            />
          </div>

          {/* Filter Buttons */}
          <div className="grid grid-cols-3 gap-1 bg-crust p-0.5 rounded-lg border border-surface1/30">
            {(['all', 'agents', 'skills'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setExplorerFilter(filter)}
                className={`text-[10px] py-1 font-semibold rounded cursor-pointer transition-all uppercase ${
                  explorerFilter === filter 
                    ? 'bg-surface1 text-text shadow-sm' 
                    : 'text-overlay2 hover:text-text'
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-1.5 flex flex-col gap-1">
          {filteredExplorerItems.length > 0 ? (
            filteredExplorerItems.map(item => {
              const selected = selectedExplorer?.type === item.type && selectedExplorer?.name === item.name;
              const Icon = item.type === 'agent' ? Bot : Wrench;
              const colorClass = item.type === 'agent' ? 'text-blue' : 'text-mauve';
              const selectedBg = item.type === 'agent' 
                ? 'bg-blue/5 text-blue border-l-3 border-l-blue' 
                : 'bg-mauve/5 text-mauve border-l-3 border-l-mauve';
              
              return (
                <div 
                  key={`${item.type}-${item.name}`}
                  onClick={() => setSelectedExplorer({ type: item.type, name: item.name })}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer text-xs transition-all ${
                    selected ? selectedBg : 'hover:bg-white/[0.01] text-subtext1'
                  }`}
                >
                  <Icon className={`h-4 w-4 shrink-0 ${selected ? colorClass : 'text-overlay1'}`} />
                  <div className="flex flex-col truncate">
                    <span className="font-semibold truncate">{item.name}</span>
                    <span className="text-[9px] text-overlay1 uppercase font-bold tracking-wide mt-0.5">
                      {item.type}
                    </span>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center text-xs text-overlay0 py-8">No results found</div>
          )}
        </div>
      </aside>

      {/* Explorer detailed pane */}
      <div className="flex-1 overflow-y-auto bg-base p-6">
        {loadingExplorer ? (
          <div className="h-full w-full flex items-center justify-center text-blue">
            <Sliders className="h-8 w-8 animate-spin" />
          </div>
        ) : explorerDetail ? (
          <div className="flex flex-col gap-6 max-w-[800px]">
            <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-sm flex flex-col gap-4 relative overflow-hidden">
              {/* Banner decor */}
              <div className={`absolute top-0 left-0 w-2.5 h-full ${
                selectedExplorer?.type === 'agent' ? 'bg-blue' : 'bg-mauve'
              }`} />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {selectedExplorer?.type === 'agent' ? (
                    <Bot className="h-8 w-8 text-blue bg-blue/10 p-1.5 rounded-lg" />
                  ) : (
                    <Wrench className="h-8 w-8 text-mauve bg-mauve/10 p-1.5 rounded-lg" />
                  )}
                  <div>
                    <h2 className="text-lg font-bold font-display text-text">{explorerDetail.name}</h2>
                    <p className="text-[10px] font-bold text-overlay1 uppercase tracking-wider mt-0.5">
                      Custom {selectedExplorer?.type} details
                    </p>
                  </div>
                </div>
                <span className={`text-[10px] font-mono font-bold px-3 py-1 rounded-full uppercase border ${
                  selectedExplorer?.type === 'agent' 
                    ? 'bg-blue/10 text-blue border-blue/20' 
                    : 'bg-mauve/10 text-mauve border-mauve/20'
                }`}>
                  {selectedExplorer?.type}
                </span>
              </div>

              {explorerDetail.metadata.description && (
                <p className="text-sm text-subtext1 leading-relaxed border-t border-surface0/60 pt-3">
                  {explorerDetail.metadata.description}
                </p>
              )}

              {Object.keys(explorerDetail.metadata).filter(k => k !== 'description').length > 0 && (
                <div className="flex flex-wrap gap-2 mt-1 border-t border-surface0/60 pt-3">
                  {Object.entries(explorerDetail.metadata)
                    .filter(([k]) => k !== 'description')
                    .map(([k, v]) => (
                      <span key={k} className="text-[10px] font-mono px-2 py-0.5 bg-crust text-overlay1 rounded border border-surface1">
                        {k}: {String(v)}
                      </span>
                    ))}
                </div>
              )}
            </div>

            {/* Markdown instructions */}
            <div className="bg-mantle border border-surface0 rounded-xl p-6 shadow-sm flex flex-col gap-3">
              <div className="text-xs font-bold font-display text-overlay2 uppercase tracking-wider border-b border-surface0 pb-2">
                System Prompt Instructions
              </div>
              <div 
                className="markdown-body prose prose-invert max-w-none text-sm text-subtext1 leading-relaxed font-sans"
                dangerouslySetInnerHTML={{ __html: marked.parse(explorerDetail.prompt) }}
              />
            </div>
          </div>
        ) : (
          <div className="h-full w-full flex flex-col items-center justify-center text-overlay0">
            <Compass className="h-12 w-12 text-surface2 mb-2 animate-pulse" />
            <span>Select an agent or skill from the left list to review detailed configurations.</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExplorerTab;
