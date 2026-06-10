import type { ReactNode } from 'react';

interface TokenStatsProps {
  icon: ReactNode;
  label: string;
  value: string;
  color: string;
}

export function TokenStats({ icon, label, value, color }: TokenStatsProps) {
  return (
    <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl glass hover:border-accent/20 transition-colors">
      <div className={`${color} opacity-90`}>{icon}</div>
      <div>
        <div className="text-[10px] text-text-muted uppercase tracking-wider font-semibold mb-0.5">{label}</div>
        <div className="font-mono text-sm font-bold text-text-primary">{value}</div>
      </div>
    </div>
  );
}
