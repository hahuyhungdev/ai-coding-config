import React from 'react';
import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import type { FullConfig } from '../../../../types';
import { Alert, Button, Group, Text, Badge } from '@mantine/core';

export interface GraphifyStatusProps {
  tempConfig: FullConfig;
  rebuilding: boolean;
  onRebuild: () => Promise<void>;
}

export const GraphifyStatus: React.FC<GraphifyStatusProps> = ({
  tempConfig,
  rebuilding,
  onRebuild
}) => {
  const health = tempConfig.graphify_health;

  if (!health) return null;

  const isMissing = !health.graph_exists;
  const isStale = health.is_stale;

  const color = isMissing ? 'red' : isStale ? 'yellow' : 'green';
  const title = isMissing
    ? 'Graphify Index Missing'
    : isStale
      ? 'Graphify Index Stale'
      : 'Graphify Index Healthy';

  const icon = isMissing ? (
    <AlertTriangle size={20} className="text-error animate-pulse" />
  ) : isStale ? (
    <AlertTriangle size={20} className="text-warning animate-bounce" />
  ) : (
    <CheckCircle2 size={20} className="text-success" />
  );

  return (
    <Alert
      color={color}
      title={
        <Group gap="xs">
          <span style={{ fontWeight: 600 }}>{title}</span>
          {health.graph_exists && (
            <Badge color={color} variant="light" size="xs">
              {health.graph_size_kb} KB
            </Badge>
          )}
        </Group>
      }
      icon={icon}
      variant="light"
      className="animate-fade-up"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <Text size="xs" className="leading-relaxed max-w-2xl text-text-secondary">
            {isMissing
              ? 'Your codebase has not been semantic-indexed yet. Run the installer or trigger a rebuild to initialize the Graphify index.'
              : isStale
                ? `${health.stale_reason} Trigger a rebuild to refresh the index.`
                : `Active Graphify index is synchronized with commit ${health.current_commit}. Last built: ${health.last_built}`}
          </Text>
          {health.graph_exists && !health.git_hooks_installed && (
            <Group gap="xs" mt={8}>
              <AlertTriangle size={12} className="text-warning shrink-0" />
              <Text size="11px" fw={500} className="text-warning">
                Git hooks are not fully configured. Background auto-updates will not trigger.
              </Text>
            </Group>
          )}
        </div>

        {health.graph_exists && (
          <Button
            color={color}
            onClick={onRebuild}
            disabled={rebuilding}
            leftSection={<RefreshCw size={13} className={rebuilding ? "animate-spin" : ""} />}
            size="xs"
            className="shrink-0"
          >
            {rebuilding ? 'Rebuilding...' : 'Rebuild Graph'}
          </Button>
        )}
      </div>
    </Alert>
  );
};
