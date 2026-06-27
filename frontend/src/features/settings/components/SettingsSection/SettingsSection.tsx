import React from 'react';
import { ClaudeTab } from "../ClaudeTab/ClaudeTab";
import { McpTab } from "../McpTab/McpTab";
import CodexTab from "../CodexTab/CodexTab";
import GeminiTab from "../GeminiTab/GeminiTab";
import type { FullConfig } from '../../../../types';

interface SettingsSectionProps {
  activeTab: string;
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  handleClaudeEnvChange: (key: string, value: string) => void;
  handleClaudePermsChange: (key: string, value: string) => void;
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

export function SettingsSection({
  activeTab,
  initialConfig,
  tempConfig,
  setTempConfig,
  handleClaudeEnvChange,
  handleClaudePermsChange,
  selectedMcpServer,
  setSelectedMcpServer,
  filteredMcp,
  mcpSearch,
  setMcpSearch,
  handleMcpToggle,
  deleteCustomMcp,
  setShowAddMcpModal,
  showToast
}: SettingsSectionProps) {
  switch (activeTab) {
    case "mcp":
      return (
        <McpTab
          tempConfig={tempConfig}
          setTempConfig={setTempConfig}
          selectedMcpServer={selectedMcpServer}
          setSelectedMcpServer={setSelectedMcpServer}
          filteredMcp={filteredMcp}
          mcpSearch={mcpSearch}
          setMcpSearch={setMcpSearch}
          handleMcpToggle={handleMcpToggle}
          deleteCustomMcp={deleteCustomMcp}
          setShowAddMcpModal={setShowAddMcpModal}
          showToast={showToast}
        />
      );
    case "claude":
      return (
        <ClaudeTab
          initialConfig={initialConfig}
          tempConfig={tempConfig}
          setTempConfig={setTempConfig}
          handleClaudeEnvChange={handleClaudeEnvChange}
          handleClaudePermsChange={handleClaudePermsChange}
        />
      );
    case "codex":
      return (
        <CodexTab
          initialConfig={initialConfig}
          tempConfig={tempConfig}
          setTempConfig={setTempConfig}
        />
      );
    case "gemini":
      return (
        <GeminiTab
          initialConfig={initialConfig}
          tempConfig={tempConfig}
          setTempConfig={setTempConfig}
        />
      );
    default:
      return null;
  }
}
