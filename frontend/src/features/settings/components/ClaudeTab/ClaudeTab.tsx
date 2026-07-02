import React from 'react';
import type { FullConfig } from '../../../../types';
import { Toggle } from '../../../../components/Toggle';
import {
  TextInput,
  Select,
  Button,
  Modal,
  Textarea,
  Card,
  Text,
  Stack,
  Group,
  Title,
  Badge
} from '@mantine/core';
import { Sliders, ShieldCheck, FileText } from 'lucide-react';

interface ClaudeTabProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
  handleClaudeEnvChange: (key: string, value: string) => void;
  handleClaudePermsChange: (key: string, value: string) => void;
}

export const ClaudeTab: React.FC<ClaudeTabProps> = ({
  initialConfig,
  tempConfig,
  setTempConfig,
  handleClaudeEnvChange,
  handleClaudePermsChange
}) => {
  const [showInstructions, setShowInstructions] = React.useState(false);
  const isInstructionsModified = initialConfig.claude_instructions !== tempConfig.claude_instructions;

  return (
    <div className="flex flex-col gap-5 w-full">
      <div>
        <Title order={2} className="font-display text-text-primary mb-1">Claude Code</Title>
        <Text size="sm" c="dimmed">Configure LLM environment and permission policies</Text>
      </div>

      <div className="flex flex-col gap-5">
        {/* Card 1: LLM & Environment */}
        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-1">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <Sliders size={18} className="text-info" />
            <Text size="sm" fw={600} className="text-info">LLM & Environment Configuration</Text>
          </Group>

          <Stack gap="md">
            <TextInput
              label="Max Thinking Tokens"
              type="number"
              value={tempConfig.claude.env?.MAX_THINKING_TOKENS || ''}
              placeholder="20000"
              onChange={e => handleClaudeEnvChange('MAX_THINKING_TOKENS', e.currentTarget.value)}
              error={
                (initialConfig.claude.env?.MAX_THINKING_TOKENS || '20000') !== (tempConfig.claude.env?.MAX_THINKING_TOKENS || '')
                  ? 'Staged Changes Pending'
                  : undefined
              }
            />

            <TextInput
              label="Max Output Tokens"
              type="number"
              value={tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || ''}
              placeholder="12000"
              onChange={e => handleClaudeEnvChange('CLAUDE_CODE_MAX_OUTPUT_TOKENS', e.currentTarget.value)}
              error={
                (initialConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '12000') !== (tempConfig.claude.env?.CLAUDE_CODE_MAX_OUTPUT_TOKENS || '')
                  ? 'Staged Changes Pending'
                  : undefined
              }
            />

            <TextInput
              label="Autocompact % Override"
              type="number"
              value={tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || ''}
              placeholder="60"
              onChange={e => handleClaudeEnvChange('CLAUDE_AUTOCOMPACT_PCT_OVERRIDE', e.currentTarget.value)}
              error={
                (initialConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '60') !== (tempConfig.claude.env?.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE || '')
                  ? 'Staged Changes Pending'
                  : undefined
              }
            />

            <Select
              label="No-Flicker Mode"
              value={tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true'}
              onChange={val => handleClaudeEnvChange('CLAUDE_CODE_NO_FLICKER', val || 'true')}
              data={[
                { value: 'true', label: 'Enabled — Prevents terminal layout redraws' },
                { value: 'false', label: 'Disabled — Forces raw terminal outputs' },
              ]}
              error={
                (initialConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || 'true') !== (tempConfig.claude.env?.CLAUDE_CODE_NO_FLICKER || '')
                  ? 'Staged Changes Pending'
                  : undefined
              }
            />

            <div>
              <Text size="sm" fw={500} mb={4}>Instructions Guide</Text>
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
                Edit CLAUDE.md Instructions
              </Button>
            </div>
          </Stack>
        </Card>

        {/* Card 2: Security & Permissions */}
        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-2">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <ShieldCheck size={18} className="text-info" />
            <Text size="sm" fw={600} className="text-info">Security & Permission Policies</Text>
          </Group>

          <Stack gap="md">
            <Select
              label="Default Permission Mode"
              value={tempConfig.claude.permissions?.defaultMode || 'ask'}
              onChange={val => handleClaudePermsChange('defaultMode', val || 'ask')}
              data={[
                { value: 'ask', label: 'Ask — Interactive authorization prompts' },
                { value: 'allow', label: 'Allow — Auto-approve non-dangerous tasks' },
              ]}
              error={
                (initialConfig.claude.permissions?.defaultMode || 'ask') !== (tempConfig.claude.permissions?.defaultMode || 'ask')
                  ? 'Staged Changes Pending'
                  : undefined
              }
            />

            <Group justify="space-between">
              <Text size="sm" fw={500}>Skip Dangerous Warning:</Text>
              <Toggle
                checked={!!tempConfig.claude.skipDangerousModePermissionPrompt}
                onChange={() => setTempConfig(prev => prev ? {
                  ...prev,
                  claude: {
                    ...prev.claude,
                    skipDangerousModePermissionPrompt: !prev.claude.skipDangerousModePermissionPrompt
                  }
                } : null)}
              />
            </Group>
          </Stack>
        </Card>
      </div>

      {/* Instructions Modal */}
      <Modal
        opened={showInstructions}
        onClose={() => setShowInstructions(false)}
        title={
          <Group gap="xs">
            <FileText size={16} className="text-info" />
            <Text size="sm" fw={600}>CLAUDE.md Instructions</Text>
          </Group>
        }
        size="lg"
        centered
      >
        <Stack gap="md">
          <Textarea
            value={tempConfig.claude_instructions || ''}
            onChange={e => setTempConfig(prev => prev ? { ...prev, claude_instructions: e.currentTarget.value } : null)}
            placeholder="# Claude Code Instructions..."
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
