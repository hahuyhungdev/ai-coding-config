import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  BarChart2, Cpu, Zap, DollarSign, Clock, Search, 
  TrendingUp, Calendar, MessageSquare 
} from 'lucide-react';
import { formatDate, formatTokens, formatCost } from '../../utils/format';

interface SessionAnalytics {
  id: string;
  title: string;
  last_updated: string;
  size_bytes: number;
  source: string;
  project: string;
  steps: number;
  turns: number;
  tool_calls: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost: number;
  model_name: string;
}

interface AnalyticsData {
  total_sessions: number;
  total_steps: number;
  total_turns: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  sessions: SessionAnalytics[];
}

export const AnalyticsTab: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'gemini' | 'claude' | 'codex'>('all');

  useEffect(() => {
    fetch('/api/analytics')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch analytics data');
        return res.json();
      })
      .then(json => {
        setData(json);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-text-muted">
        <div className="w-12 h-12 rounded-xl bg-accent/10 border border-accent/25 flex items-center justify-center glow-pulse animate-spin">
          <BarChart2 size={24} className="text-accent" />
        </div>
        <div className="text-sm font-medium">Aggregating token & session metrics...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-error">
        <div className="text-lg font-semibold">Error Loading Analytics</div>
        <div className="text-sm opacity-80">{error || 'No analytics data available.'}</div>
      </div>
    );
  }

  // Calculate Flash vs Pro rates
  const proEquivalentCost = data.sessions.reduce((acc, s) => {
    // Pro rates: $1.25 / 1M input, $5.00 / 1M output
    const sCostPro = (s.input_tokens / 1_000_000.0) * 1.25 + (s.output_tokens / 1_000_000.0) * 5.00;
    return acc + sCostPro;
  }, 0);

  const savings = Math.max(0, proEquivalentCost - data.total_cost);
  const savingsPercent = proEquivalentCost > 0 ? (savings / proEquivalentCost) * 100 : 0;

  // Calculate source breakdowns
  const sourceStats = data.sessions.reduce((acc, s) => {
    const src = s.source || 'gemini';
    if (!acc[src]) acc[src] = { tokens: 0, cost: 0, count: 0 };
    acc[src].tokens += s.total_tokens;
    acc[src].cost += s.cost;
    acc[src].count += 1;
    return acc;
  }, {} as Record<string, { tokens: number; cost: number; count: number }>);

  // Filter sessions
  const filteredSessions = data.sessions.filter(s => {
    const matchesSearch = s.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.project.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSource = sourceFilter === 'all' || s.source === sourceFilter;
    return matchesSearch && matchesSource;
  });

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="font-display font-bold text-2xl text-text-primary mb-1">
          Observability & Token Analytics
        </h1>
        <p className="text-[13px] text-text-muted">
          Aggregated resource and cost metrics across all configured AI coding assistants.
        </p>
      </div>

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-accent mb-2 opacity-90"><MessageSquare size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">Sessions</div>
            <div className="font-mono text-lg font-bold text-text-primary">{data.total_sessions}</div>
          </div>
        </div>
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-accent mb-2 opacity-90"><Cpu size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">Total Steps</div>
            <div className="font-mono text-lg font-bold text-text-primary">{data.total_steps.toLocaleString()}</div>
          </div>
        </div>
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-accent mb-2 opacity-90"><Clock size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">User Turns</div>
            <div className="font-mono text-lg font-bold text-text-primary">{data.total_turns.toLocaleString()}</div>
          </div>
        </div>
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-accent mb-2 opacity-90"><Zap size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">Input Tokens</div>
            <div className="font-mono text-lg font-bold text-text-primary">{formatTokens(data.total_input_tokens)}</div>
          </div>
        </div>
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-success mb-2 opacity-90"><Zap size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">Output Tokens</div>
            <div className="font-mono text-lg font-bold text-text-primary">{formatTokens(data.total_output_tokens)}</div>
          </div>
        </div>
        <div className="glass hover-lift px-5 py-4 rounded-xl flex flex-col justify-between">
          <div className="text-warning mb-2 opacity-90"><DollarSign size={16} /></div>
          <div>
            <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">Total Cost</div>
            <div className="font-mono text-lg font-bold text-text-primary">{formatCost(data.total_cost)}</div>
          </div>
        </div>
      </div>

      {/* Two Column Graphs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Savings Analysis */}
        <div className="glass p-6 rounded-xl space-y-5">
          <div className="flex items-center gap-2">
            <TrendingUp className="text-success" size={16} />
            <h2 className="font-display font-semibold text-sm text-text-primary uppercase tracking-wider">
              Cost Leverage: Pro vs. Flash
            </h2>
          </div>
          
          <div className="space-y-4">
            {/* Pro Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-text-secondary">Gemini 3.5 Pro (Equivalent)</span>
                <span className="font-mono">{formatCost(proEquivalentCost)}</span>
              </div>
              <div className="h-6 bg-white/[0.04] rounded-lg overflow-hidden border border-white/[0.06] flex items-center">
                <div className="h-full bg-error/45 transition-all duration-500 w-full" />
              </div>
            </div>

            {/* Flash Bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-success">Gemini 3.5 Flash (Actual)</span>
                <span className="font-mono text-success font-bold">{formatCost(data.total_cost)}</span>
              </div>
              <div className="h-6 bg-white/[0.04] rounded-lg overflow-hidden border border-white/[0.06] flex items-center">
                <div 
                  className="h-full bg-success/60 shadow-[0_0_12px_rgba(80,250,123,0.3)] transition-all duration-500 w-[var(--flash-width)]" 
                  {...{ style: { '--flash-width': `${Math.max(4, (data.total_cost / Math.max(1, proEquivalentCost)) * 100)}%` } as React.CSSProperties }}
                />
              </div>
            </div>
          </div>

          <div className="bg-success-dim border border-success/15 rounded-xl px-4 py-3 text-xs text-success leading-relaxed flex flex-col gap-1">
            <div className="font-bold uppercase tracking-wider text-[10px] mb-0.5">💰 Pricing Impact Result</div>
            Running your agent loops on Gemini 3.5 Flash saved you <strong>{formatCost(savings)} ({savingsPercent.toFixed(1)}% savings)</strong> compared to the Pro model tier, while supporting active 2M token context sizes.
          </div>
        </div>

        {/* Source Distribution */}
        <div className="glass p-6 rounded-xl space-y-5">
          <div className="flex items-center gap-2">
            <BarChart2 className="text-accent" size={16} />
            <h2 className="font-display font-semibold text-sm text-text-primary uppercase tracking-wider">
              Token Volume by Assistant
            </h2>
          </div>

          <div className="space-y-4">
            {['gemini', 'claude', 'codex'].map(src => {
              const stats = sourceStats[src] || { tokens: 0, cost: 0, count: 0 };
              const grandTotal = Object.values(sourceStats).reduce((a, b) => a + b.tokens, 0) || 1;
              const pct = (stats.tokens / grandTotal) * 100;
              
              const barColor = 
                src === 'claude' ? 'bg-orange-500/50' : 
                src === 'codex' ? 'bg-emerald-500/50' : 
                'bg-cyan-500/50';

              return (
                <div key={src} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="capitalize font-medium text-text-secondary">{src === 'gemini' ? 'gemini (agy)' : src}</span>
                    <span className="font-mono opacity-80">{formatTokens(stats.tokens)} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="h-3.5 bg-white/[0.04] rounded-full overflow-hidden border border-white/[0.06]">
                    <div 
                      className={`h-full ${barColor} rounded-full transition-all duration-500 w-[var(--bar-width)]`} 
                      {...{ style: { '--bar-width': `${pct}%` } as React.CSSProperties }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border border-white/[0.08] bg-white/[0.02] rounded-xl px-4 py-3 text-xs text-text-muted leading-relaxed">
            💡 <strong>Observation:</strong> Higher step counts in agent loops generate rapid context growth. Enabling Graphify AST caching maps references semantically, reducing context overheads by up to 99.8%.
          </div>
        </div>
      </div>

      {/* Directory Table */}
      <div className="glass rounded-xl overflow-hidden">
        {/* Table Toolbar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 px-5 py-4 border-b border-white/[0.08] bg-white/[0.03]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/15 flex items-center justify-center">
              <Calendar size={15} className="text-accent" />
            </div>
            <div>
              <span className="font-display font-semibold text-sm text-text-primary block">Session History Directory</span>
              <span className="text-[11px] text-text-muted">Showing {filteredSessions.length} of {data.total_sessions} historical debug runs</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted/60" />
              <input 
                type="text" 
                placeholder="Filter history..." 
                value={searchQuery} 
                onChange={e => setSearchQuery(e.target.value)}
                className="bg-white/[0.04] border border-white/[0.10] rounded-lg py-2 pl-9 pr-3 text-xs text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:border-accent/40 transition-all duration-300 w-full sm:w-56" 
              />
            </div>

            {/* Filter Toggle */}
            <div className="flex border border-white/[0.08] bg-white/[0.03] rounded-lg p-0.5">
              {(['all', 'gemini', 'claude', 'codex'] as const).map(src => (
                <button
                  key={src}
                  onClick={() => setSourceFilter(src)}
                  className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider cursor-pointer transition-all ${
                    sourceFilter === src 
                      ? 'bg-accent/15 text-accent border border-accent/20' 
                      : 'text-text-muted/70 border border-transparent hover:text-text-secondary'
                  }`}
                >
                  {src === 'gemini' ? 'agy' : src}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Table Body */}
        <div className="overflow-x-auto">
          {filteredSessions.length === 0 ? (
            <div className="text-center py-10 text-xs text-text-muted">
              No matching conversations found.
            </div>
          ) : (
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-text-muted/75 font-semibold bg-white/[0.01]">
                  <th className="py-3 px-5">Session / Source</th>
                  <th className="py-3 px-4">Steps / Turns</th>
                  <th className="py-3 px-4">Total Tokens</th>
                  <th className="py-3 px-4">Cost (Flash)</th>
                  <th className="py-3 px-4">Date Updated</th>
                  <th className="py-3 px-5 text-right">Model</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredSessions.map(s => {
                  const badgeColor = 
                    s.source === 'claude' ? 'bg-orange-500/15 text-orange-400 border border-orange-500/20' : 
                    s.source === 'codex' ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 
                    'bg-cyan-500/15 text-cyan-400 border border-cyan-500/20';

                  return (
                    <tr 
                      key={s.id} 
                      onClick={() => navigate(`/conversations?id=${s.id}`)}
                      className="hover:bg-white/[0.04] transition-colors group cursor-pointer"
                    >
                      <td className="py-4 px-5 max-w-xs">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${badgeColor}`}>
                            {s.source || 'gemini'}
                          </span>
                          <span className="font-mono text-text-muted/75 text-[11px]">#{s.id.split('__').pop()?.slice(0, 8)}</span>
                        </div>
                        <div className="font-semibold text-text-primary group-hover:text-accent transition-colors leading-snug line-clamp-1">
                          {s.title}
                        </div>
                      </td>
                      <td className="py-4 px-4 font-mono">
                        <div className="text-text-primary font-bold">{s.steps} steps</div>
                        <div className="text-text-muted text-[10px]">{s.turns} turns</div>
                      </td>
                      <td className="py-4 px-4 font-mono font-bold text-text-secondary">
                        {formatTokens(s.total_tokens)}
                      </td>
                      <td className="py-4 px-4 font-mono font-bold text-success">
                        {formatCost(s.cost)}
                      </td>
                      <td className="py-4 px-4 text-text-muted">
                        {formatDate(s.last_updated)}
                      </td>
                      <td className="py-4 px-5 text-right font-mono text-text-muted/80 text-[11px]">
                        {s.model_name}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
