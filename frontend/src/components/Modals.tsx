import React from 'react';
import { Modal, TextInput, Select, Textarea, Button, Group, Stack, Text } from '@mantine/core';
import { Cpu, Save, AlertTriangle } from 'lucide-react';

// --- ADD MCP MODAL ---
interface AddMcpModalProps {
  isOpen: boolean;
  onClose: () => void;
  newMcpName: string;
  setNewMcpName: (val: string) => void;
  newMcpType: 'stdio' | 'sse';
  setNewMcpType: (val: 'stdio' | 'sse') => void;
  newMcpCommand: string;
  setNewMcpCommand: (val: string) => void;
  newMcpArgs: string;
  setNewMcpArgs: (val: string) => void;
  newMcpEnv: string;
  setNewMcpEnv: (val: string) => void;
  newMcpUrl: string;
  setNewMcpUrl: (val: string) => void;
  onAdd: () => void;
}

export const AddMcpModal: React.FC<AddMcpModalProps> = ({
  isOpen, onClose,
  newMcpName, setNewMcpName,
  newMcpType, setNewMcpType,
  newMcpCommand, setNewMcpCommand,
  newMcpArgs, setNewMcpArgs,
  newMcpEnv, setNewMcpEnv,
  newMcpUrl, setNewMcpUrl,
  onAdd,
}) => {
  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={
        <Group gap="xs">
          <Cpu size={16} className="text-accent" />
          <Text size="sm" fw={600}>Add MCP Server</Text>
        </Group>
      }
      centered
      size="md"
    >
      <Stack gap="md">
        <TextInput
          label="Server Identifier"
          placeholder="e.g. mysql-connector"
          value={newMcpName}
          onChange={(e) => setNewMcpName(e.currentTarget.value)}
          data-autofocus
        />

        <Select
          label="Connection Protocol"
          value={newMcpType}
          onChange={(val) => setNewMcpType(val as 'stdio' | 'sse')}
          data={[
            { value: 'stdio', label: 'stdio — Command Line' },
            { value: 'sse', label: 'sse — HTTP Server-Sent Events' },
          ]}
        />

        {newMcpType === 'stdio' ? (
          <>
            <TextInput
              label="Executable Command"
              placeholder="e.g. npx"
              value={newMcpCommand}
              onChange={(e) => setNewMcpCommand(e.currentTarget.value)}
            />

            <Textarea
              label="Arguments"
              description="One per line"
              rows={3}
              placeholder={"e.g.\n-y\n@modelcontextprotocol/server-postgres\npostgresql://localhost/postgres"}
              value={newMcpArgs}
              onChange={(e) => setNewMcpArgs(e.currentTarget.value)}
            />

            <Textarea
              label="Environment Variables (JSON)"
              description="JSON format"
              rows={3}
              placeholder={'e.g. {\n  "PORT": "3306"\n}'}
              value={newMcpEnv}
              onChange={(e) => setNewMcpEnv(e.currentTarget.value)}
            />
          </>
        ) : (
          <TextInput
            label="URL"
            placeholder="https://mcp.server.com/mcp"
            value={newMcpUrl}
            onChange={(e) => setNewMcpUrl(e.currentTarget.value)}
          />
        )}

        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button color="indigo" onClick={onAdd}>
            Add Server
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

// --- APPLY CHANGES MODAL ---
interface ApplyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (force: boolean) => void;
}

export const ApplyModal: React.FC<ApplyModalProps> = ({ isOpen, onClose, onApply }) => {
  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={
        <Group gap="xs">
          <Save size={16} className="text-success" />
          <Text size="sm" fw={600}>Apply Staged Changes?</Text>
        </Group>
      }
      centered
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          This will write configuration settings to the repository templates and invoke the global installation script to sync CLI files.
        </Text>
        <Text size="sm" c="dimmed">
          Choose <strong>Standard Apply</strong> for standard config mapping, or <strong className="text-warning">Force Overwrite</strong> to overwrite all destination files completely.
        </Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button color="orange" onClick={() => onApply(true)}>
            Force Overwrite
          </Button>
          <Button color="green" onClick={() => onApply(false)}>
            Standard Apply
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};

// --- DISCARD CHANGES MODAL ---
interface DiscardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDiscard: () => void;
}

export const DiscardModal: React.FC<DiscardModalProps> = ({ isOpen, onClose, onDiscard }) => {
  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={
        <Group gap="xs">
          <AlertTriangle size={16} className="text-error" />
          <Text size="sm" fw={600}>Discard Changes?</Text>
        </Group>
      }
      centered
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          Are you sure you want to discard all staged configuration changes? All modified fields will revert to their original saved values immediately.
        </Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button color="red" onClick={onDiscard}>
            Discard Changes
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
};
