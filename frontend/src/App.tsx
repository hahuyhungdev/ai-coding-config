import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Sliders,
  LayoutDashboard,
  Cpu,
  MessageSquareCode,
  Terminal as TerminalIcon,
  Sparkles,
  Compass,
  MessageSquare,
  Play,
  Share2,
} from "lucide-react";

import { ToastContainer } from "./components/Toast";
import { Sidebar } from "./components/Sidebar";
import { ApplyModal, DiscardModal } from "./components/Modals";
import { DashboardTab } from "./features/dashboard";
import { SettingsSection } from "./features/settings";
import { ExplorerTab } from "./features/explorer";
import { SimulatorTab } from "./features/simulator";
import { ConversationViewer } from "./features/conversations";
import { GraphTab } from "./features/graph";
import { AnalyticsTab } from "./features/analytics";
import { useToast } from "./hooks/useToast";
import { useConfig } from "./hooks/useConfig";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "mcp", label: "MCP", icon: Cpu },
  { id: "claude", label: "Claude", icon: MessageSquareCode },
  { id: "codex", label: "Codex", icon: TerminalIcon },
  { id: "gemini", label: "Gemini", icon: Sparkles },
  { id: "explorer", label: "Agents", icon: Compass },
  { id: "conversations", label: "Observability", icon: MessageSquare },
  { id: "graph", label: "Code Graph", icon: Share2 },
  { id: "simulator", label: "Simulator", icon: Play },
];

export default function App() {
  const { toasts, showToast } = useToast();
  const config = useConfig(showToast);

  const navigate = useNavigate();
  const location = useLocation();
  const rawPath = location.pathname.substring(1);
  const activeTab = TABS.some((t) => t.id === rawPath) ? rawPath : "dashboard";
  const setActiveTab = (tabId: string) => navigate(`/${tabId}`);

  const [mcpSearch, setMcpSearch] = useState("");
  const [explorerFilter, setExplorerFilter] = useState<
    "all" | "agents" | "skills"
  >("all");
  const [selectedExplorer, setSelectedExplorer] = useState<{
    type: "agent" | "skill";
    name: string;
  } | null>(null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showDiscardModal, setShowDiscardModal] = useState(false);
  const [showMainSidebar, setShowMainSidebar] = useState(false);

  if (!config.tempConfig || !config.initialConfig) {
    return (
      <div className="flex h-screen w-full items-center justify-center">
        <div className="flex flex-col items-center gap-5 animate-fade-in">
          <div className="h-12 w-12 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center glow-pulse">
            <Sliders className="h-6 w-6 text-accent animate-spin" />
          </div>
          <span className="font-display text-lg text-text-primary">
            Loading Config Engine...
          </span>
          <span className="text-[11px] text-text-muted">
            Preparing your workspace
          </span>
        </div>
      </div>
    );
  }

  const filteredMcp = config.tempConfig.all_mcp.filter((s) =>
    s.toLowerCase().includes(mcpSearch.toLowerCase()),
  );
  const pendingChanges = config.getPendingChanges();
  const hasPendingChanges = pendingChanges.length > 0;
  const mappedPendingChanges = pendingChanges.map((c) => ({
    key: c.key,
    text: c.text,
    type: c.type === "remove" ? ("del" as const) : c.type,
  }));

  return (
    <div className="flex w-full h-screen overflow-hidden bg-bg text-text-primary max-w-[1440px] mx-auto border-x border-white/[0.08] shadow-2xl">
      {activeTab !== "conversations" && activeTab !== "graph" && (
        <>
          {/* Main Sidebar Wrapper */}
          <div
            className={`fixed inset-y-0 left-0 z-20 lg:relative lg:z-0 lg:flex shrink-0 ${
              showMainSidebar ? "flex" : "hidden"
            }`}
          >
            <Sidebar
              initialConfig={config.initialConfig}
              tempConfig={config.tempConfig}
              handleTargetToggle={config.handleTargetToggle}
              handleMcpToggle={config.handleMcpToggle}
              batchMcp={config.batchMcp}
              mcpSearch={mcpSearch}
              setMcpSearch={setMcpSearch}
              filteredMcp={filteredMcp}
              hasPendingChanges={hasPendingChanges}
              pendingChanges={mappedPendingChanges}
              setShowApplyModal={setShowApplyModal}
              setShowDiscardModal={setShowDiscardModal}
              onClose={() => setShowMainSidebar(false)}
            />
          </div>
          {/* Mobile Overlay backdrop */}
          {showMainSidebar && (
            <div
              onClick={() => setShowMainSidebar(false)}
              className="fixed inset-0 bg-black/50 z-10 lg:hidden backdrop-blur-sm animate-fade-in"
            />
          )}
        </>
      )}

      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="block bg-surface/40 backdrop-blur-md border-b border-white/[0.08] overflow-hidden shrink-0 w-full">
          <div
            className={`flex items-center justify-between overflow-hidden px-4 sm:px-6 w-full mx-auto ${
              activeTab === "conversations" || activeTab === "graph"
                ? "max-w-[1400px]"
                : "max-w-[1000px]"
            }`}
          >
            <div className="flex items-center gap-2 flex-1 overflow-hidden">
              {activeTab !== "conversations" && activeTab !== "graph" && (
                <button
                  onClick={() => setShowMainSidebar(!showMainSidebar)}
                  className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-white/[0.06] text-text-secondary hover:text-text-primary transition-colors cursor-pointer shrink-0 focus-visible:ring-2 focus-visible:ring-accent focus:outline-none"
                  title="Toggle Sidebar"
                >
                  <Sliders className="h-4 w-4" />
                </button>
              )}
              <nav className="flex gap-1.5 overflow-x-auto whitespace-nowrap scrollbar-none py-2.5 flex-1 max-w-full">
                {TABS.map((tab, i) => {
                  const Icon = tab.icon;
                  const active = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`relative flex items-center gap-2 py-2 px-3 sm:px-4 text-[12px] font-semibold rounded-lg transition-all duration-300 cursor-pointer flex-shrink-0 animate-fade-up border stagger-${i + 1} focus-visible:ring-2 focus-visible:ring-accent focus:outline-none ${
                        active
                          ? "text-accent bg-accent-dim border-accent/20 shadow-sm"
                          : "text-text-muted border-transparent hover:text-text-secondary hover:bg-white/[0.04]"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </nav>
            </div>
            <div className="hidden md:flex items-center gap-3 shrink-0 ml-4">
              <span className="text-[10px] text-text-muted bg-white/[0.03] border border-white/[0.10] px-3 py-1 rounded-full font-mono tracking-wide">
                v1.0
              </span>
            </div>
          </div>
        </header>

        {/* Content */}
        {activeTab === "conversations" ? (
          <div className="flex-1 overflow-hidden p-6 animate-fade-up w-full max-w-[1400px] mx-auto">
            <ConversationViewer fallback={<AnalyticsTab />} />
          </div>
        ) : activeTab === "graph" ? (
          <div className="flex-1 overflow-hidden p-6 animate-fade-up w-full max-w-[1400px] mx-auto">
            <GraphTab />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto main-content-scrollbar">
            <div className="p-6 sm:p-8 animate-fade-up w-full max-w-[1000px] mx-auto">
              {activeTab === "dashboard" && (
                <DashboardTab
                  tempConfig={config.tempConfig}
                  logs={config.logs}
                  setLogs={config.setLogs}
                  setActiveTab={setActiveTab}
                  setExplorerFilter={setExplorerFilter}
                  setSelectedExplorer={setSelectedExplorer}
                  fetchConfig={config.fetchConfig}
                />
              )}
              {["mcp", "claude", "codex", "gemini"].includes(activeTab) && (
                <SettingsSection
                  activeTab={activeTab}
                  initialConfig={config.initialConfig}
                  tempConfig={config.tempConfig}
                  setTempConfig={config.setTempConfig}
                  handleClaudeEnvChange={config.handleClaudeEnvChange}
                  handleClaudePermsChange={config.handleClaudePermsChange}
                  filteredMcp={filteredMcp}
                  mcpSearch={mcpSearch}
                  setMcpSearch={setMcpSearch}
                  handleMcpToggle={config.handleMcpToggle}
                  showToast={showToast}
                />
              )}
              {activeTab === "explorer" && (
                <ExplorerTab
                  tempConfig={config.tempConfig}
                  selectedExplorer={selectedExplorer}
                  setSelectedExplorer={setSelectedExplorer}
                  showToast={showToast}
                  explorerFilter={explorerFilter}
                  setExplorerFilter={setExplorerFilter}
                />
              )}
              {activeTab === "simulator" && <SimulatorTab />}
            </div>
          </div>
        )}
      </main>

      <ToastContainer toasts={toasts} />
      <ApplyModal
        isOpen={showApplyModal}
        onClose={() => setShowApplyModal(false)}
        onApply={(force) => {
          config.executeApply(force, {
            claude: config.tempConfig!.targets.claude,
            codex: config.tempConfig!.targets.codex,
            agy: config.tempConfig!.targets.agy,
          });
          setShowApplyModal(false);
        }}
      />
      <DiscardModal
        isOpen={showDiscardModal}
        onClose={() => setShowDiscardModal(false)}
        onDiscard={() => {
          config.executeDiscard();
          setShowDiscardModal(false);
        }}
      />
    </div>
  );
}
