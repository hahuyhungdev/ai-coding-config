import { useState, useCallback } from 'react';
import type { FullConfig } from '../../../types';

const DEFAULT_SERVERS = new Set(["playwright", "context7", "memory", "sequential-thinking", "postgres", "sqlite", "docker", "aws"]);

export function useMcpForm(
  tempConfig: FullConfig | null,
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>,
  setSelectedMcpServer: (s: string | null) => void,
  showToast: (msg: string, type?: 'success' | 'error' | 'warning') => void
) {
  const [showAddMcpModal, setShowAddMcpModal] = useState(false);
  const [newMcpName, setNewMcpName] = useState('');
  const [newMcpType, setNewMcpType] = useState<'stdio' | 'sse'>('stdio');
  const [newMcpCommand, setNewMcpCommand] = useState('');
  const [newMcpArgs, setNewMcpArgs] = useState('');
  const [newMcpUrl, setNewMcpUrl] = useState('');
  const [newMcpEnv, setNewMcpEnv] = useState('');

  const addCustomMcp = useCallback(() => {
    if (!tempConfig) return;
    const name = newMcpName.trim().toLowerCase();
    if (!name) { showToast("Server name is required", "error"); return; }
    if (tempConfig.all_mcp.includes(name)) { showToast(`Server "${name}" already exists`, "error"); return; }

    let envObj: Record<string, string> = {};
    if (newMcpEnv.trim()) {
      try { envObj = JSON.parse(newMcpEnv); } catch { showToast("Invalid Environment JSON", "error"); return; }
    }

    const argsArr = newMcpArgs.split('\n').map(a => a.trim()).filter(Boolean);
    const serverConfig: Record<string, unknown> = {};
    if (newMcpType === 'sse') { serverConfig.type = 'sse'; serverConfig.url = newMcpUrl.trim(); }
    else { serverConfig.command = newMcpCommand.trim(); if (argsArr.length > 0) serverConfig.args = argsArr; if (Object.keys(envObj).length > 0) serverConfig.env = envObj; }

    setTempConfig(prev => prev ? { ...prev, all_mcp: [...prev.all_mcp, name], mcp_servers: { ...prev.mcp_servers, [name]: serverConfig } } : null);
    setSelectedMcpServer(name);
    setShowAddMcpModal(false);
    setNewMcpName(''); setNewMcpCommand(''); setNewMcpArgs(''); setNewMcpUrl(''); setNewMcpEnv('');
    showToast(`Custom MCP server "${name}" added to staging!`, "success");
  }, [tempConfig, newMcpName, newMcpType, newMcpCommand, newMcpArgs, newMcpUrl, newMcpEnv, setTempConfig, setSelectedMcpServer, showToast]);

  const deleteCustomMcp = useCallback((name: string) => {
    if (!tempConfig || DEFAULT_SERVERS.has(name)) return;
    setTempConfig(prev => {
      if (!prev) return null;
      const restServers = { ...prev.mcp_servers };
      delete restServers[name];
      return { ...prev, all_mcp: prev.all_mcp.filter(s => s !== name), disabled_mcp: prev.disabled_mcp.filter(s => s !== name), mcp_servers: restServers };
    });
    const remaining = tempConfig.all_mcp.filter(s => s !== name);
    setSelectedMcpServer(remaining.length > 0 ? remaining[0] : null);
    showToast(`MCP server "${name}" removed!`, "warning");
  }, [tempConfig, setTempConfig, setSelectedMcpServer, showToast]);

  return {
    showAddMcpModal, setShowAddMcpModal,
    newMcpName, setNewMcpName,
    newMcpType, setNewMcpType,
    newMcpCommand, setNewMcpCommand,
    newMcpArgs, setNewMcpArgs,
    newMcpUrl, setNewMcpUrl,
    newMcpEnv, setNewMcpEnv,
    addCustomMcp, deleteCustomMcp
  };
}
