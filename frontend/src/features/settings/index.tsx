import React, { useState } from 'react';
import { ClaudeTab } from "./components/ClaudeTab/ClaudeTab";
import { McpTab } from "./components/McpTab/McpTab";
import CodexTab from "./components/CodexTab/CodexTab";
import GeminiTab from "./components/GeminiTab/GeminiTab";
import type { FullConfig } from '../../types';
import { useMcpForm } from './hooks/useMcpForm';
import { AddMcpModal } from '../../components/Modals';

interface SettingsSectionProps {
  activeTab: string;
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  handleClaudeEnvChange: (key: string, value: string) => void;
  handleClaudePermsChange: (key: string, value: string) => void;
  filteredMcp: string[];
  mcpSearch: string;
  setMcpSearch: (val: string) => void;
  handleMcpToggle: (server: string) => void;
  showToast: (msg: string, type?: 'success' | 'error' | 'warning') => void;
}

export function SettingsSection({
  activeTab,
  initialConfig,
  tempConfig,
  setTempConfig,
  handleClaudeEnvChange,
  handleClaudePermsChange,
  filteredMcp,
  mcpSearch,
  setMcpSearch,
  handleMcpToggle,
  showToast
}: SettingsSectionProps) {
  const [selectedMcpServer, setSelectedMcpServer] = useState<string | null>(null);
  const mcpForm = useMcpForm(
    tempConfig,
    setTempConfig,
    setSelectedMcpServer,
    showToast
  );

  switch (activeTab) {
    case "mcp":
      return (
        <>
          <McpTab
            tempConfig={tempConfig}
            setTempConfig={setTempConfig}
            selectedMcpServer={selectedMcpServer}
            setSelectedMcpServer={setSelectedMcpServer}
            filteredMcp={filteredMcp}
            mcpSearch={mcpSearch}
            setMcpSearch={setMcpSearch}
            handleMcpToggle={handleMcpToggle}
            deleteCustomMcp={mcpForm.deleteCustomMcp}
            setShowAddMcpModal={mcpForm.setShowAddMcpModal}
            showToast={showToast}
          />
          <AddMcpModal
            isOpen={mcpForm.showAddMcpModal}
            onClose={() => mcpForm.setShowAddMcpModal(false)}
            newMcpName={mcpForm.newMcpName}
            setNewMcpName={mcpForm.setNewMcpName}
            newMcpType={mcpForm.newMcpType}
            setNewMcpType={mcpForm.setNewMcpType}
            newMcpCommand={mcpForm.newMcpCommand}
            setNewMcpCommand={mcpForm.setNewMcpCommand}
            newMcpArgs={mcpForm.newMcpArgs}
            setNewMcpArgs={mcpForm.setNewMcpArgs}
            newMcpUrl={mcpForm.newMcpUrl}
            setNewMcpUrl={mcpForm.setNewMcpUrl}
            newMcpEnv={mcpForm.newMcpEnv}
            setNewMcpEnv={mcpForm.setNewMcpEnv}
            onAdd={mcpForm.addCustomMcp}
          />
        </>
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
