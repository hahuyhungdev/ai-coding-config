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
  Badge
} from '@mantine/core';

interface GeminiTabProps {
  initialConfig: FullConfig;
  tempConfig: FullConfig;
  setTempConfig: React.Dispatch<React.SetStateAction<FullConfig | null>>;
}

const GeminiTab: React.FC<GeminiTabProps> = ({ initialConfig, tempConfig, setTempConfig }) => {
  const [showInstructions, setShowInstructions] = React.useState(false);
  const isInstructionsModified = initialConfig.gemini_instructions !== tempConfig.gemini_instructions;

  const handleGeminiChange = (key: string, value: string | boolean | string[]) => {
    setTempConfig(prev => prev ? { ...prev, gemini: { ...prev.gemini, [key]: value } } : null);
  };
  const handleWorkspacesChange = (text: string) => {
    handleGeminiChange('trustedWorkspaces', text.split('\n').map(l => l.trim()).filter(Boolean));
  };

  const trustedWorkspacesText = (tempConfig.gemini.trustedWorkspaces || []).join('\n');
  const accentColor = "text-[#f59e0b]";

  return (
    <div className="flex flex-col gap-5 w-full">
      <div>
        <Title order={2} className="font-display text-text-primary mb-1">Antigravity CLI</Title>
        <Text size="sm" c="dimmed">Configure Gemini model and workspace trust</Text>
      </div>

      <div className="flex flex-col gap-5">
        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-1">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <Sliders size={18} className="text-[#f59e0b]" />
            <Text size="sm" fw={600} className="text-[#f59e0b]">LLM & Environment</Text>
          </Group>

          <Stack gap="md">
            <TextInput
              label="Model Alias"
              placeholder="Gemini 3.5 Flash"
              value={tempConfig.gemini.model || ''}
              onChange={e => handleGeminiChange('model', e.currentTarget.value)}
              error={(initialConfig.gemini.model || '') !== (tempConfig.gemini.model || '') ? 'Staged Changes Pending' : undefined}
            />

            <Group justify="space-between">
              <Text size="sm" fw={500}>Enable Telemetry:</Text>
              <Toggle checked={!!tempConfig.gemini.enableTelemetry} onChange={val => handleGeminiChange('enableTelemetry', val)} />
            </Group>

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
                Edit ANTIGRAVITY.md
              </Button>
            </div>
          </Stack>
        </Card>

        <Card withBorder radius="md" p="xl" className="glass animate-fade-up stagger-2">
          <Group gap="xs" pb="xs" mb="md" style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <ShieldCheck size={18} className="text-[#f59e0b]" />
            <Text size="sm" fw={600} className="text-[#f59e0b]">Security & Permissions</Text>
          </Group>

          <Stack gap="md">
            <Select
              label="Tool Permission"
              value={tempConfig.gemini.toolPermission || 'always-ask'}
              onChange={val => handleGeminiChange('toolPermission', val || 'always-ask')}
              data={[
                { value: 'always-ask', label: 'Always Ask — Prompt for permissions' },
                { value: 'always-proceed', label: 'Always Proceed — Auto-approve tools' },
              ]}
              error={(initialConfig.gemini.toolPermission || '') !== (tempConfig.gemini.toolPermission || '') ? 'Staged Changes Pending' : undefined}
            />

            <Textarea
              label="Trusted Workspaces"
              placeholder="/path/to/project1\n/path/to/project2"
              rows={4}
              value={trustedWorkspacesText}
              onChange={e => handleWorkspacesChange(e.currentTarget.value)}
              styles={{ input: { fontFamily: 'var(--font-mono)' } }}
              error={JSON.stringify(initialConfig.gemini.trustedWorkspaces || []) !== JSON.stringify(tempConfig.gemini.trustedWorkspaces || []) ? 'Staged Changes Pending' : undefined}
            />
          </Stack>
        </Card>
      </div>

      <Modal
        opened={showInstructions}
        onClose={() => setShowInstructions(false)}
        title={
          <Group gap="xs">
            <FileText size={16} className={accentColor} />
            <Text size="sm" fw={600}>ANTIGRAVITY.md Instructions</Text>
          </Group>
        }
        size="lg"
        centered
      >
        <Stack gap="md">
          <Textarea
            value={tempConfig.gemini_instructions || ''}
            onChange={e => setTempConfig(prev => prev ? { ...prev, gemini_instructions: e.currentTarget.value } : null)}
            placeholder="# Antigravity CLI Instructions..."
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

export default GeminiTab;
