import { useState } from 'react';
import { Share2, GitFork, ExternalLink } from 'lucide-react';

export function GraphTab() {
  const [project, setProject] = useState('mswcc-front-fe');
  const [viewType, setViewType] = useState<'graph' | 'tree'>('graph');

  const iframeSrc = `/api/graphify/view?project=${project}&type=${viewType}`;

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
          </div>

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

      {/* Interactive Graph Iframe Container */}
      <div className="flex-1 w-full h-full bg-[#1b1c23]/60 relative">
        <iframe
          src={iframeSrc}
          className="w-full h-full border-none"
          title="Graphify Visualization"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}
