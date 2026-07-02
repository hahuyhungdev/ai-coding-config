import React from 'react';
import { Sliders, ShieldCheck, FileText } from 'lucide-react';
import type { FullConfig } from '../../../../types';
import { Toggle } from '../../../../components/Toggle';
import {
  TextInput,
  Select,
  Textarea,
  Button,
  Modal,
  Card,
  Text,
  Stack,
  Group,
  Title,
  SimpleGrid,
  Badge
} from '@mantine/core';

interface CodexTabProps {
  tempConfig: FullConfig;
  initialConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const CodexTab: React.FC<CodexTabProps> = ({ tempConfig, initialConfig, setTempConfig }) => {
  const [showInstructions, setShowInstructions] = React.useState(false);

  const handleCodexChange = (key: string, value: string) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, [key]: value } } : null);
  };
  const handleCodexFeatureChange = (key: string, value: boolean) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, features: { ...prev.codex.features, [key]: value } } } : null);
  };
  const handleCodexNoticeChange = (key: string, value: boolean) => {
    setTempConfig(prev => prev ? { ...prev, codex: { ...prev.codex, notice: { ...prev.codex.notice, [key]: value } } } : null);
  };

  const isInstructionsModified = initialConfig.codex_instructions !== tempConfig.codex_instructions;
  const accentColor = "text-success";

  return (
    <div className="flex flex-col gap-5 w-full">
      <div>
        <Title order={2} className="font-display text-text-primary mb-1">Codex CLI</Title>
        <Text size="sm" c="dimmed">Configure model, security, and agent behavior</Text>
      </div>

      <div className="flex flex-col gap-5">
        {/* LLM & Environment */}
        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-1">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <Sliders size={18} className="text-success" />
            <Text size="sm" fw={600} className="text-success">LLM & Environment</Text>
          </Group>

          <Stack gap="md">
            <TextInput
              label="Model Alias"
              placeholder="gpt-5.5"
              value={tempConfig.codex.model || ''}
              onChange={e => handleCodexChange('model', e.currentTarget.value)}
              error={initialConfig.codex.model !== tempConfig.codex.model ? 'Staged Changes Pending' : undefined}
            />

            <Select
              label="Reasoning Effort"
              value={tempConfig.codex.model_reasoning_effort || 'medium'}
              onChange={val => handleCodexChange('model_reasoning_effort', val || 'medium')}
              data={[
                { value: 'low', label: 'Low — Faster, less depth' },
                { value: 'medium', label: 'Medium — Balanced execution' },
                { value: 'high', label: 'High — Deep thinking for complex goals' },
              ]}
              error={initialConfig.codex.model_reasoning_effort !== tempConfig.codex.model_reasoning_effort ? 'Staged Changes Pending' : undefined}
            />

            <Select
              label="Web Search"
              value={tempConfig.codex.web_search || 'live'}
              onChange={val => handleCodexChange('web_search', val || 'live')}
              data={[
                { value: 'live', label: 'Live — Enabled' },
                { value: 'disabled', label: 'Offline — Disabled' },
              ]}
              error={initialConfig.codex.web_search !== tempConfig.codex.web_search ? 'Staged Changes Pending' : undefined}
            />

            <Textarea
              label="Persistent Instructions"
              placeholder="System prompts for every init..."
              rows={3}
              value={tempConfig.codex.persistent_instructions || ''}
              onChange={e => handleCodexChange('persistent_instructions', e.currentTarget.value)}
              styles={{ input: { fontFamily: 'var(--font-mono)' } }}
              error={initialConfig.codex.persistent_instructions !== tempConfig.codex.persistent_instructions ? 'Staged Changes Pending' : undefined}
            />

            <div>
              <Text size="sm" fw={500} mb={4}>Instructions</Text>
              <Button
                variant={isInstructionsModified ? 'light' : 'default'}
                color={isInstructionsModified ? 'orange' : 'indigo'}
                fullWidth
                onClick={() => setShowInstructions(true)}
                leftSection={<FileText size={16} />}
                rightSection={
                  isInstructionsModified && (
                    <Badge color="orange" size="xs">
                      Modified
                    </Badge>
                  )
                }
              >
                Edit AGENTS.md
              </Button>
            </div>
          </Stack>
        </Card>

        {/* Security & Permissions */}
        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-2">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <ShieldCheck size={18} className="text-success" />
            <Text size="sm" fw={600} className="text-success">Security & Permissions</Text>
          </Group>

          <Stack gap="md">
            <Select
              label="Approval Policy"
              value={tempConfig.codex.approval_policy || 'on-request'}
              onChange={val => handleCodexChange('approval_policy', val || 'on-request')}
              data={[
                { value: 'on-request', label: 'On Request' },
                { value: 'always', label: 'Always' },
                { value: 'never', label: 'Never' },
              ]}
              error={initialConfig.codex.approval_policy !== tempConfig.codex.approval_policy ? 'Staged Changes Pending' : undefined}
            />

            <Select
              label="Sandbox Mode"
              value={tempConfig.codex.sandbox_mode || 'workspace-write'}
              onChange={val => handleCodexChange('sandbox_mode', val || 'workspace-write')}
              data={[
                { value: 'workspace-write', label: 'Workspace Write' },
                { value: 'read-only', label: 'Read Only' },
                { value: 'workspace-read', label: 'Workspace Read' },
              ]}
              error={initialConfig.codex.sandbox_mode !== tempConfig.codex.sandbox_mode ? 'Staged Changes Pending' : undefined}
            />

            <Select
              label="Approvals Reviewer"
              value={tempConfig.codex.approvals_reviewer || 'user'}
              onChange={val => handleCodexChange('approvals_reviewer', val || 'user')}
              data={[
                { value: 'user', label: 'User — Manual approval' },
                { value: 'auto', label: 'Auto — Bypass manual checks' },
              ]}
              error={initialConfig.codex.approvals_reviewer !== tempConfig.codex.approvals_reviewer ? 'Staged Changes Pending' : undefined}
            />

            {/* Feature toggles */}
            <div className="border-t border-white/[0.08] pt-4 mt-2">
              <Text size="xs" fw={700} c="dimmed" style={{ letterSpacing: '0.15px', textTransform: 'uppercase' }} mb="xs">
                Features & Warnings
              </Text>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                {[
                  { key: 'memories', label: 'Persistent Memories', desc: 'Allow agent to store details', checked: !!tempConfig.codex.features?.memories, onChange: (v: boolean) => handleCodexFeatureChange('memories', v) },
                  { key: 'multi_agent', label: 'Multi-Agent Loops', desc: 'Activate subagent spawning', checked: !!tempConfig.codex.features?.multi_agent, onChange: (v: boolean) => handleCodexFeatureChange('multi_agent', v) },
                  { key: 'hide_warn', label: 'Hide Full Access Notice', desc: 'Bypasses startup prompt', checked: !!tempConfig.codex.notice?.hide_full_access_warning, onChange: (v: boolean) => handleCodexNoticeChange('hide_full_access_warning', v) },
                  { key: 'opt_out', label: 'Default Opt-out Warning', desc: 'Fast-track opt out warnings', checked: !!tempConfig.codex.notice?.fast_default_opt_out, onChange: (v: boolean) => handleCodexNoticeChange('fast_default_opt_out', v) },
                ].map(item => (
                  <Group key={item.key} justify="space-between" p="sm" className="bg-white/[0.04] border border-white/[0.08]" style={{ borderRadius: 'var(--radius-lg)' }}>
                    <div>
                      <Text size="xs" fw={500} className="text-text-secondary">{item.label}</Text>
                      <Text size="10px" c="dimmed" mt={2}>{item.desc}</Text>
                    </div>
                    <Toggle checked={item.checked} onChange={item.onChange} />
                  </Group>
                ))}
              </SimpleGrid>
            </div>
          </Stack>
        </Card>
      </div>

      {/* Instructions Modal */}
      <Modal
        opened={showInstructions}
        onClose={() => setShowInstructions(false)}
        title={
          <Group gap="xs">
            <FileText size={16} className={accentColor} />
            <Text size="sm" fw={600}>AGENTS.md Instructions</Text>
          </Group>
        }
        size="lg"
        centered
      >
        <Stack gap="md">
          <Textarea
            value={tempConfig.codex_instructions || ''}
            onChange={e => setTempConfig(prev => prev ? { ...prev, codex_instructions: e.currentTarget.value } : null)}
            placeholder="# Codex CLI Instructions..."
            rows={15}
            styles={{ input: { fontFamily: 'var(--font-mono)', fontSize: '13px' } }}
          />
          <Text size="xs" c="dimmed">
            Press Close to keep staged edits. Changes are saved when you click Apply.
          </Text>
          <Group justify="flex-end">
            <Button color="indigo" onClick={() => setShowInstructions(false)}>
              Close & Stage
            </Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  );
};

export default CodexTab;
