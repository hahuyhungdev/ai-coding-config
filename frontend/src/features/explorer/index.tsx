import { useState, useEffect } from 'react';
import { Search, Bot, Wrench, Compass } from 'lucide-react';
import { marked } from 'marked';
import type { FullConfig, ExplorerDetail } from '../../types';
import {
  TextInput,
  SegmentedControl,
  ScrollArea,
  Loader,
  Card,
  Badge,
  Text,
  Group,
  Stack,
  Title
} from '@mantine/core';

interface ExplorerTabProps {
  tempConfig: FullConfig;
  selectedExplorer: { type: 'agent' | 'skill'; name: string } | null;
  setSelectedExplorer: (val: { type: 'agent' | 'skill'; name: string } | null) => void;
  showToast: (msg: string, type: 'success' | 'error' | 'warning') => void;
  explorerFilter: 'all' | 'agents' | 'skills';
  setExplorerFilter: (filter: 'all' | 'agents' | 'skills') => void;
}

export function ExplorerTab({
  tempConfig, selectedExplorer, setSelectedExplorer, showToast, explorerFilter, setExplorerFilter,
}: ExplorerTabProps) {
  const [explorerSearch, setExplorerSearch] = useState<string>('');
  const [explorerDetail, setExplorerDetail] = useState<ExplorerDetail | null>(null);
  const [loadingExplorer, setLoadingExplorer] = useState<boolean>(false);
  const [prevSelected, setPrevSelected] = useState<{ type: 'agent' | 'skill'; name: string } | null>(null);

  if (selectedExplorer !== prevSelected) {
    setPrevSelected(selectedExplorer);
    if (!selectedExplorer) {
      setExplorerDetail(null);
    }
  }

  useEffect(() => {
    if (!selectedExplorer) return;
    let active = true;

    const fetchExplorerDetail = async (type: 'agent' | 'skill', name: string) => {
      setLoadingExplorer(true);
      try {
        const res = await fetch(`/api/${type}/${name}`);
        if (!res.ok) throw new Error(`Failed to load ${type}`);
        const data = await res.json();
        if (active) {
          setExplorerDetail(data);
        }
      } catch (err: unknown) {
        if (active) {
          const errMsg = err instanceof Error ? err.message : String(err);
          showToast(errMsg, 'error');
          setExplorerDetail(null);
        }
      } finally {
        if (active) {
          setLoadingExplorer(false);
        }
      }
    };

    fetchExplorerDetail(selectedExplorer.type, selectedExplorer.name);
    return () => {
      active = false;
    };
  }, [selectedExplorer, showToast]);

  const filteredExplorerItems = [
    ...(explorerFilter === 'all' || explorerFilter === 'agents' ? tempConfig.agents.map(a => ({ type: 'agent' as const, name: a })) : []),
    ...(explorerFilter === 'all' || explorerFilter === 'skills' ? tempConfig.skills.map(s => ({ type: 'skill' as const, name: s })) : [])
  ].filter(item => item.name.toLowerCase().includes(explorerSearch.toLowerCase()));

  return (
    <div className="flex h-[calc(100vh-180px)] glass rounded-xl overflow-hidden">
      {/* Sidebar list */}
      <aside className="w-[290px] border-r border-white/[0.08] flex flex-col shrink-0 bg-white/[0.03]">
        <div className="p-4 border-b border-white/[0.08] flex flex-col gap-3">
          <TextInput
            placeholder="Search..."
            leftSection={<Search size={14} />}
            value={explorerSearch}
            onChange={e => setExplorerSearch(e.currentTarget.value)}
          />
          <SegmentedControl
            value={explorerFilter}
            onChange={val => setExplorerFilter(val as 'all' | 'agents' | 'skills')}
            data={[
              { label: 'ALL', value: 'all' },
              { label: 'AGENTS', value: 'agents' },
              { label: 'SKILLS', value: 'skills' },
            ]}
          />
        </div>

        <ScrollArea className="flex-1 p-1.5">
          <Stack gap={4}>
            {filteredExplorerItems.length > 0 ? filteredExplorerItems.map(item => {
              const selected = selectedExplorer?.type === item.type && selectedExplorer?.name === item.name;
              const Icon = item.type === 'agent' ? Bot : Wrench;
              const borderClass = selected 
                ? (item.type === 'agent' ? 'border-l-[#0052a3] text-[#0052a3] bg-white/[0.04]' : 'border-l-[#ff4500] text-[#ff4500] bg-white/[0.04]') 
                : 'hover:bg-white/[0.04] text-text-secondary border-l-2 border-transparent';
              const iconColorClass = selected
                ? (item.type === 'agent' ? 'text-[#0052a3]' : 'text-[#ff4500]')
                : 'text-text-muted';
              return (
                <div key={`${item.type}-${item.name}`} onClick={() => setSelectedExplorer({ type: item.type, name: item.name })}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg cursor-pointer text-xs transition-all duration-200 ${borderClass}`}>
                  <Icon className={`h-4 w-4 shrink-0 ${iconColorClass}`} />
                  <div className="flex flex-col truncate">
                    <span className="font-medium truncate">{item.name}</span>
                    <span className="text-[9px] text-text-muted uppercase tracking-wide mt-0.5">{item.type}</span>
                  </div>
                </div>
              );
            }) : (
              <div className="text-center text-xs text-text-muted py-8">No results</div>
            )}
          </Stack>
        </ScrollArea>
      </aside>
 
      {/* Detail pane */}
      <ScrollArea className="flex-1 p-6">
        {loadingExplorer ? (
          <div className="h-full w-full flex items-center justify-center py-20">
            <Loader size="md" color="indigo" />
          </div>
        ) : explorerDetail ? (
          <div className="flex flex-col gap-5 max-w-[800px] animate-fade-up">
            <Card withBorder radius="md" p="xl" className="glass relative overflow-hidden">
              <div className={`absolute top-0 left-0 w-1 h-full ${
                selectedExplorer?.type === 'agent' ? 'bg-[#0052a3]' : 'bg-[#ff4500]'
              }`} />
              <Group justify="space-between" mb="md">
                <Group gap="md">
                  {selectedExplorer?.type === 'agent' ? (
                    <div className="h-10 w-10 rounded-lg bg-info-dim border border-info/15 flex items-center justify-center">
                      <Bot className="h-5 w-5 text-info" />
                    </div>
                  ) : (
                    <div className="h-10 w-10 rounded-lg bg-accent-dim border border-accent/15 flex items-center justify-center">
                      <Wrench className="h-5 w-5 text-accent" />
                    </div>
                  )}
                  <div>
                    <Title order={3} className="text-lg font-display text-text-primary">{explorerDetail.name}</Title>
                    <Text size="10px" c="dimmed" style={{ letterSpacing: '0.12px', textTransform: 'uppercase' }} mt={2}>
                      {selectedExplorer?.type} details
                    </Text>
                  </div>
                </Group>
                <Badge color={selectedExplorer?.type === 'agent' ? 'blue' : 'orange'} variant="light" size="sm">
                  {selectedExplorer?.type}
                </Badge>
              </Group>

              {explorerDetail.metadata.description && (
                <Text size="sm" className="text-text-secondary leading-relaxed border-t border-white/[0.08] pt-3">
                  {explorerDetail.metadata.description}
                </Text>
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
            </Card>

            <Card withBorder radius="md" p="xl" className="glass">
              <Text size="10px" fw={700} c="dimmed" style={{ letterSpacing: '0.15px', textTransform: 'uppercase', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }} pb="xs" mb="md">
                System Prompt
              </Text>
              <div
                className="prose prose-invert max-w-none text-sm text-text-secondary leading-relaxed"
                dangerouslySetInnerHTML={{ __html: marked.parse(explorerDetail.prompt) }}
              />
            </Card>
          </div>
        ) : (
          <div className="h-full w-full flex flex-col items-center justify-center text-text-muted py-20">
            <Compass className="h-12 w-12 opacity-15 mb-3 animate-pulse" />
            <Text size="sm">Select an agent or skill to view details</Text>
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
