import React, { useState } from 'react';
import type { FullConfig } from '../../../../types';
import { Toggle } from '../../../../components/Toggle';
import {
  TextInput,
  Select,
  Textarea,
  Button,
  Group,
  Stack,
  Text,
  Badge,
  Alert,
  ScrollArea,
} from '@mantine/core';
import {
  Search, Plus, Cpu, Play, Save, Trash as TrashIcon,
  CheckCircle2, AlertTriangle, XCircle, Sliders
} from 'lucide-react';

interface McpTabProps {
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  selectedMcpServer: string | null;
  setSelectedMcpServer: (server: string | null) => void;
  filteredMcp: string[];
  mcpSearch: string;
  setMcpSearch: (val: string) => void;
  handleMcpToggle: (server: string) => void;
  deleteCustomMcp: (server: string) => void;
  setShowAddMcpModal: (show: boolean) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'warning') => void;
}

const DEFAULT_SERVERS = new Set(["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]);

export const McpTab: React.FC<McpTabProps> = ({
  tempConfig,
  setTempConfig,
  selectedMcpServer,
  setSelectedMcpServer,
  filteredMcp,
  mcpSearch,
  setMcpSearch,
  handleMcpToggle,
  deleteCustomMcp,
  setShowAddMcpModal,
  showToast
}) => {
  const [mcpEditorType, setMcpEditorType] = useState<'stdio' | 'sse'>('stdio');
  const [mcpEditorCommand, setMcpEditorCommand] = useState<string>('');
  const [mcpEditorArgs, setMcpEditorArgs] = useState<string>('');
  const [mcpEditorUrl, setMcpEditorUrl] = useState<string>('');
  const [mcpEditorEnv, setMcpEditorEnv] = useState<string>('');
  const [mcpTestStatus, setMcpTestStatus] = useState<'idle' | 'testing' | 'success' | 'error' | 'warning'>('idle');
  const [mcpTestMessage, setMcpTestMessage] = useState<string>('');

  const [prevSelectedMcpServer, setPrevSelectedMcpServer] = useState<string | null>(null);
  const [prevTempConfig, setPrevTempConfig] = useState<FullConfig | null>(null);

  if (selectedMcpServer !== prevSelectedMcpServer || tempConfig !== prevTempConfig) {
    setPrevSelectedMcpServer(selectedMcpServer);
    setPrevTempConfig(tempConfig);
    setMcpTestStatus('idle');
    setMcpTestMessage('');
    if (selectedMcpServer && tempConfig) {
      const config = tempConfig.mcp_servers[selectedMcpServer] || {};
      const isSse = config.type === 'sse' || !!config.url;
      setMcpEditorType(isSse ? 'sse' : 'stdio');
      setMcpEditorCommand((config.command as string) || '');
      setMcpEditorUrl((config.url as string) || '');
      if (Array.isArray(config.args)) {
        setMcpEditorArgs(config.args.join('\n'));
      } else {
        setMcpEditorArgs(config.args ? String(config.args) : '');
      }
      if (config.env) {
        setMcpEditorEnv(JSON.stringify(config.env, null, 2));
      } else {
        setMcpEditorEnv('');
      }
    }
  }

  const saveMcpEditor = () => {
    if (!selectedMcpServer) return;
    let envObj: Record<string, string> = {};
    if (mcpEditorEnv.trim()) {
      try { envObj = JSON.parse(mcpEditorEnv); }
      catch { showToast("Invalid Environment JSON. Please verify syntax.", "error"); return; }
    }
    const argsArr = mcpEditorArgs.split('\n').map(a => a.trim()).filter(Boolean);
    const updatedServerConfig: Record<string, unknown> = {};
    if (mcpEditorType === 'sse') {
      updatedServerConfig.type = 'sse';
      updatedServerConfig.url = mcpEditorUrl.trim();
    } else {
      updatedServerConfig.command = mcpEditorCommand.trim();
      if (argsArr.length > 0) updatedServerConfig.args = argsArr;
      if (Object.keys(envObj).length > 0) updatedServerConfig.env = envObj;
    }
    setTempConfig(prev => {
      if (!prev) return null;
      return { ...prev, mcp_servers: { ...prev.mcp_servers, [selectedMcpServer]: updatedServerConfig } };
    });
    showToast(`MCP server "${selectedMcpServer}" configuration staged!`, "success");
  };

  const testMcpConfig = async () => {
    if (!selectedMcpServer) return;
    setMcpTestStatus('testing');
    setMcpTestMessage('Testing configuration availability...');
    let envObj = {};
    if (mcpEditorEnv.trim()) {
      try { envObj = JSON.parse(mcpEditorEnv); }
      catch { setMcpTestStatus('error'); setMcpTestMessage('Invalid Environment JSON format.'); return; }
    }
    try {
      const res = await fetch('/api/mcp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: selectedMcpServer, type: mcpEditorType, command: mcpEditorCommand, args: mcpEditorArgs.split('\n').map(a => a.trim()).filter(Boolean), env: envObj, url: mcpEditorUrl })
      });
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
      const data = await res.json();
      setMcpTestStatus(data.status);
      setMcpTestMessage(data.message);
      if (data.status === 'success') showToast('MCP test passed!', 'success');
      else if (data.status === 'warning') showToast('MCP test warning: command exists but failed run.', 'warning');
      else showToast('MCP test failed.', 'error');
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMcpTestStatus('error');
      setMcpTestMessage(`Test error: ${errMsg}`);
      showToast(`Test failed: ${errMsg}`, 'error');
    }
  };

  return (
    <div className="flex h-[calc(100vh-180px)] glass rounded-xl overflow-hidden">
      {/* Left pane — Server selector */}
      <aside className="w-[280px] border-r border-white/[0.08] flex flex-col shrink-0 bg-white/[0.03]">
        <div className="p-4 border-b border-white/[0.08]">
          <TextInput
            placeholder="Search servers..."
            leftSection={<Search size={14} />}
            value={mcpSearch}
            onChange={e => setMcpSearch(e.currentTarget.value)}
          />
        </div>

        <ScrollArea className="flex-1 p-2">
          <Stack gap={4}>
            {filteredMcp.map(server => {
              const isDisabled = tempConfig.disabled_mcp.includes(server);
              const selected = selectedMcpServer === server;
              return (
                <div
                  key={server}
                  onClick={() => setSelectedMcpServer(server)}
                  className={`flex items-center justify-between px-3.5 py-3 rounded-lg cursor-pointer transition-all duration-200 ${
                    selected
                      ? 'bg-accent-dim border border-accent/25 text-accent shadow-sm'
                      : 'hover:bg-accent-dim hover:text-accent text-text-secondary border border-transparent'
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-sm font-mono font-medium">{server}</span>
                    <span className="text-[10px] text-text-muted mt-0.5">
                      {DEFAULT_SERVERS.has(server) ? 'Core' : 'Custom'}
                    </span>
                  </div>
                  <Badge color={isDisabled ? 'red' : 'green'} variant="light" size="sm">
                    {isDisabled ? 'Off' : 'On'}
                  </Badge>
                </div>
              );
            })}
          </Stack>
        </ScrollArea>

        <div className="p-3 border-t border-white/[0.08]">
          <Button
            fullWidth
            color="indigo"
            onClick={() => setShowAddMcpModal(true)}
            leftSection={<Plus size={16} />}
          >
            Add Custom MCP
          </Button>
        </div>
      </aside>

      {/* Right pane — Editor */}
      <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-6">
        {selectedMcpServer ? (
          <div className="flex flex-col gap-5 max-w-[680px] animate-fade-up">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div>
                <h2 className="text-lg font-display text-accent font-mono">{selectedMcpServer}</h2>
                <p className="text-xs text-text-muted mt-1">Configure parameters for ~/.claude.json</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-text-secondary font-medium">Enable:</span>
                <Toggle checked={!tempConfig.disabled_mcp.includes(selectedMcpServer)} onChange={() => handleMcpToggle(selectedMcpServer)} />
              </div>
            </div>

            <Stack gap="md">
              <Select
                label="Connection Type"
                value={mcpEditorType}
                onChange={val => setMcpEditorType(val as 'stdio' | 'sse')}
                data={[
                  { value: 'stdio', label: 'stdio — Command Line' },
                  { value: 'sse', label: 'sse — HTTP Server-Sent Events' },
                ]}
              />

              {mcpEditorType === 'stdio' ? (
                <>
                  <TextInput
                    label="command"
                    placeholder="npx"
                    value={mcpEditorCommand}
                    onChange={e => setMcpEditorCommand(e.currentTarget.value)}
                    styles={{ input: { fontFamily: 'var(--font-mono)' } }}
                  />
                  <Textarea
                    label="args"
                    description="One per line"
                    rows={4}
                    placeholder="-y\n@modelcontextprotocol/server-postgres\npostgresql://localhost/postgres"
                    value={mcpEditorArgs}
                    onChange={e => setMcpEditorArgs(e.currentTarget.value)}
                    styles={{ input: { fontFamily: 'var(--font-mono)' } }}
                  />
                  <Textarea
                    label="env"
                    description="JSON format"
                    rows={4}
                    placeholder={'{\n  "PGPORT": "5432"\n}'}
                    value={mcpEditorEnv}
                    onChange={e => setMcpEditorEnv(e.currentTarget.value)}
                    styles={{ input: { fontFamily: 'var(--font-mono)' } }}
                  />
                </>
              ) : (
                <TextInput
                  label="url"
                  placeholder="https://mcp.context7.com/mcp"
                  value={mcpEditorUrl}
                  onChange={e => setMcpEditorUrl(e.currentTarget.value)}
                  styles={{ input: { fontFamily: 'var(--font-mono)' } }}
                />
              )}
            </Stack>

            {/* Test status */}
            {mcpTestStatus !== 'idle' && (
              <Alert
                color={
                  mcpTestStatus === 'testing' ? 'blue' :
                  mcpTestStatus === 'success' ? 'green' :
                  mcpTestStatus === 'warning' ? 'yellow' : 'red'
                }
                title={
                  mcpTestStatus === 'testing' ? 'Running Diagnostics...' :
                  mcpTestStatus === 'success' ? 'Diagnostics Passed' :
                  mcpTestStatus === 'warning' ? 'Diagnostics Warning' : 'Diagnostics Failed'
                }
                icon={
                  mcpTestStatus === 'testing' ? <Sliders className="h-4 w-4 animate-spin" /> :
                  mcpTestStatus === 'success' ? <CheckCircle2 className="h-4 w-4" /> :
                  mcpTestStatus === 'warning' ? <AlertTriangle className="h-4 w-4" /> :
                  <XCircle className="h-4 w-4" />
                }
              >
                <Text size="xs" style={{ fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
                  {mcpTestMessage}
                </Text>
              </Alert>
            )}

            {/* Actions */}
            <Group justify="space-between" mt="xl" pt="md" style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
              {!DEFAULT_SERVERS.has(selectedMcpServer) ? (
                <Button
                  color="red"
                  variant="outline"
                  leftSection={<TrashIcon size={14} />}
                  onClick={() => deleteCustomMcp(selectedMcpServer)}
                >
                  Delete Server
                </Button>
              ) : <div />}

              <Group gap="sm">
                <Button
                  variant="default"
                  leftSection={<Play size={14} className="text-accent" />}
                  onClick={testMcpConfig}
                  disabled={mcpTestStatus === 'testing'}
                >
                  Test
                </Button>
                <Button
                  color="indigo"
                  leftSection={<Save size={14} />}
                  onClick={saveMcpEditor}
                >
                  Save
                </Button>
              </Group>
            </Group>
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-text-muted">
            <Cpu className="h-12 w-12 opacity-20 mb-3" />
            <span className="text-sm">Select a server to configure</span>
          </div>
        )}
      </div>
    </div>
  );
};
