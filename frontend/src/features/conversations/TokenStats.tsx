import type { ReactNode } from 'react';

interface TokenStatsProps {
  icon: ReactNode;
  label: string;
  value: string;
  color: string;
}

export function TokenStats({ icon, label, value, color }: TokenStatsProps) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg glass">
      <div className={`${color} opacity-80`}>{icon}</div>
      <div>
        <div className="text-[9px] text-text-muted uppercase tracking-[0.12] font-semibold mb-0.5">{label}</div>
        <div className="font-mono text-[13px] font-semibold text-text-primary">{value}</div>
      </div>
    </div>
  );
}
