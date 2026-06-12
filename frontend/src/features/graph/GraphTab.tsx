import { useState } from 'react';
import { Share2, GitFork, ExternalLink, Activity, RefreshCw } from 'lucide-react';

export function GraphTab() {
  const [project, setProject] = useState('mswcc-front-fe');
  const [viewType, setViewType] = useState<'graph' | 'tree' | 'callflow'>('graph');
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [rebuildStatus, setRebuildStatus] = useState<{ type: 'success' | 'error' | null; message: string }>({ type: null, message: '' });

  const iframeSrc = `/api/graphify/view?project=${project}&type=${viewType}`;

  const handleRebuild = async () => {
    setIsRebuilding(true);
    setRebuildStatus({ type: null, message: '' });
    try {
      const response = await fetch('/api/graphify/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project, force: false }),
      });
      const data = await response.json();
      if (data.status === 'success') {
        setRebuildStatus({ type: 'success', message: 'Codebase graph updated successfully (AST-only update).' });
        // Force refresh iframe
        const iframe = document.getElementById('graphify-iframe') as HTMLIFrameElement;
        if (iframe) {
          iframe.src = iframe.src;
        }
      } else {
        setRebuildStatus({ type: 'error', message: `Update failed: ${data.stderr || data.stdout || 'Unknown error'}` });
      }
    } catch (err: any) {
      setRebuildStatus({ type: 'error', message: `Network error: ${err.message}` });
    } finally {
      setIsRebuilding(false);
      // Clear status after 6 seconds
      setTimeout(() => {
        setRebuildStatus({ type: null, message: '' });
      }, 6000);
    }
  };

  return (
    <div className="flex flex-col h-full w-full rounded-xl glass overflow-hidden animate-fade-in">
      {/* Toolbar Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 px-6 py-4 border-b border-white/[0.08] bg-white/[0.03] shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
            <Share2 size={15} className="text-accent" />
          </div>
          <div>
            <span className="font-display font-semibold text-sm text-text-primary block">Codebase Graph Visualizer</span>
            <span className="text-[11px] text-text-muted">Explore structural relationships, module communities, and dependency chains</span>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Project selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted font-medium">Project:</span>
            <select
              value={project}
              onChange={(e) => setProject(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.10] rounded-lg py-1.5 px-3 text-xs text-text-primary focus:outline-none focus:border-accent/40 cursor-pointer font-medium"
            >
              <option value="mswcc-front-fe" className="bg-bg">mswcc-front-fe</option>
              <option value="ai-coding-config" className="bg-bg">ai-coding-config</option>
            </select>
          </div>

          {/* View Type Toggle */}
          <div className="flex border border-white/[0.08] bg-white/[0.03] rounded-lg p-0.5">
            <button
              onClick={() => setViewType('graph')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider cursor-pointer transition-all ${
                viewType === 'graph'
                  ? 'bg-accent/15 text-accent border border-accent/20'
                  : 'text-text-muted border border-transparent hover:text-text-secondary'
              }`}
            >
              <Share2 size={12} />
              2D Network
            </button>
            <button
              onClick={() => setViewType('tree')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider cursor-pointer transition-all ${
                viewType === 'tree'
                  ? 'bg-accent/15 text-accent border border-accent/20'
                  : 'text-text-muted border border-transparent hover:text-text-secondary'
              }`}
            >
              <GitFork size={12} />
              Module Tree
            </button>
            <button
              onClick={() => setViewType('callflow')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[10px] font-bold uppercase tracking-wider cursor-pointer transition-all ${
                viewType === 'callflow'
                  ? 'bg-accent/15 text-accent border border-accent/20'
                  : 'text-text-muted border border-transparent hover:text-text-secondary'
              }`}
            >
              <Activity size={12} />
              Call Flow
            </button>
          </div>

          {/* Update Graph Button */}
          <button
            onClick={handleRebuild}
            disabled={isRebuilding}
            className={`flex items-center gap-1.5 py-1.5 px-3 rounded-lg border border-white/[0.10] bg-white/[0.04] text-xs text-text-primary hover:bg-white/[0.08] transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed`}
            title="Fast update graph from source files AST (No LLM)"
          >
            <RefreshCw size={12} className={isRebuilding ? 'animate-spin text-accent' : ''} />
            <span>{isRebuilding ? 'Updating...' : 'Update Graph'}</span>
          </button>

          {/* Open in new tab link */}
          <a
            href={iframeSrc}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg border border-white/[0.10] bg-white/[0.04] text-text-muted hover:text-text-secondary hover:bg-white/[0.06] transition-all duration-200 cursor-pointer flex items-center justify-center"
            title="Open in new tab"
          >
            <ExternalLink size={14} />
          </a>
        </div>
      </div>

      {/* Status banner */}
      {rebuildStatus.type && (
        <div className={`px-6 py-2 text-xs font-medium text-center border-b transition-all duration-300 animate-fade-in ${
          rebuildStatus.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' 
            : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
        }`}>
          {rebuildStatus.message}
        </div>
      )}

      {/* Interactive Graph Iframe Container */}
      <div className="flex-1 w-full h-full bg-[#1b1c23]/60 relative">
        <iframe
          id="graphify-iframe"
          src={iframeSrc}
          className="w-full h-full border-none"
          title="Graphify Visualization"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}
