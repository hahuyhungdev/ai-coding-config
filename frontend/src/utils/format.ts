import type { ConversationStep, ConversationTurn } from '../types';

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatTokens(tokens: number): string {
  if (tokens < 1000) return tokens.toString();
  if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
  return `${(tokens / 1000000).toFixed(2)}M`;
}

export function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

export function parseTurns(steps: ConversationStep[]): ConversationTurn[] {
  const turns: ConversationTurn[] = [];
  let current: ConversationTurn | null = null;

  for (const step of steps) {
    if (step.type === 'USER_INPUT') {
      if (current) turns.push(current);
      current = { index: turns.length, user: step, agent: null, tools: [] };
    } else if (step.type === 'PLANNER_RESPONSE') {
      if (!current) {
        current = { index: turns.length, user: null, agent: step, tools: [] };
      } else {
        current.agent = step;
      }
    } else {
      if (!current) {
        current = { index: turns.length, user: null, agent: null, tools: [] };
      }
      current.tools.push(step);
    }
  }
  if (current) turns.push(current);
  return turns;
}
