export interface Targets {
  claude: boolean;
  codex: boolean;
  agy: boolean;
  [key: string]: boolean;
}

export interface ClaudeConfig {
  env?: {
    MAX_THINKING_TOKENS?: string;
    CLAUDE_CODE_MAX_OUTPUT_TOKENS?: string;
    CLAUDE_AUTOCOMPACT_PCT_OVERRIDE?: string;
    CLAUDE_CODE_NO_FLICKER?: string;
    [key: string]: string | undefined;
  };
  permissions?: {
    defaultMode?: string;
    allow?: string[];
    deny?: string[];
  };
  skipDangerousModePermissionPrompt?: boolean;
}

export interface CodexConfig {
  approval_policy?: string;
  sandbox_mode?: string;
  web_search?: string;
  approvals_reviewer?: string;
  model?: string;
  model_reasoning_effort?: string;
  persistent_instructions?: string;
  features?: {
    memories?: boolean;
    multi_agent?: boolean;
  };
  notice?: {
    hide_full_access_warning?: boolean;
    fast_default_opt_out?: boolean;
  };
}

export interface GeminiConfig {
  enableTelemetry?: boolean;
  model?: string;
  toolPermission?: string;
  trustedWorkspaces?: string[];
}

export interface FullConfig {
  claude: ClaudeConfig;
  codex: CodexConfig;
  gemini: GeminiConfig;
  mcp_servers: Record<string, any>;
  all_mcp: string[];
  disabled_mcp: string[];
  gemini_instructions: string;
  claude_instructions: string;
  codex_instructions: string;
  targets: Targets;
  agents: string[];
  skills: string[];
}


export interface ExplorerDetail {
  name: string;
  metadata: {
    description?: string;
    model?: string;
    origin?: string;
    [key: string]: any;
  };
  prompt: string;
}
