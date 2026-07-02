import React, { useState, useEffect, useRef } from 'react';
import { Play, Shield, Key, HelpCircle, Check, X, Terminal, Cpu, Info, RefreshCw, Zap } from 'lucide-react';
import {
  SegmentedControl,
  Button,
  Card,
  Text,
  Title,
  Group,
  Badge,
  Center,
  Alert,
  ScrollArea
} from '@mantine/core';

interface SimulationStep {
  title: string;
  desc: string;
  icon: React.ElementType;
  status: 'pending' | 'active' | 'completed' | 'failed';
  role: 'user' | 'client' | 'cloud' | 'local';
}

const PRESETS = [
  {
    id: 'read-file',
    name: 'Đọc file App.tsx (An toàn)',
    prompt: 'Xem nội dung file App.tsx để kiểm tra import',
    toolName: 'view_file',
    args: { AbsolutePath: '/absolute/path/to/project/frontend/src/App.tsx' },
    risk: 'low',
    riskDesc: 'Đọc file (Read-only) - Tự động thực thi mà không cần duyệt.',
    output: "import React from 'react';\nimport { useState } from 'react';\n..."
  },
  {
    id: 'run-command',
    name: 'Chạy lệnh Git Status (Rủi ro cao)',
    prompt: 'Kiểm tra trạng thái Git repository',
    toolName: 'run_command',
    args: { CommandLine: 'git status' },
    risk: 'high',
    riskDesc: 'Chạy lệnh Terminal (Write/Execute) - Bắt buộc phải dừng lại chờ User duyệt.',
    output: "On branch master\nYour branch is ahead of 'origin/master' by 2 commits."
  }
];

export const SimulatorTab: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState(PRESETS[0]);
  const [mode, setMode] = useState<'simulation' | 'real'>('simulation');
  const [stepIndex, setStepIndex] = useState(-1);
  const [logs, setLogs] = useState<string[]>([]);
  const [approved, setApproved] = useState<boolean | null>(null);
  const [toolUseId, setToolUseId] = useState(() => 'toolu_' + Math.random().toString(36).substring(2, 15));

  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const addLog = (msg: string) => setLogs(prev => [...prev, msg]);

  const resetSimulation = () => {
    setStepIndex(-1);
    setLogs([]);
    setApproved(null);
    setToolUseId('toolu_' + Math.random().toString(36).substring(2, 15));
  };

  const nextStep = () => {
    const nextIdx = stepIndex + 1;
    setStepIndex(nextIdx);

    if (nextIdx === 0) {
      addLog(`[USER] Đã nhập yêu cầu: "${selectedPreset.prompt}"`);
    } else if (nextIdx === 1) {
      addLog(`[CLIENT] Gửi HTTPS POST lên Anthropic API...`);
      addLog(`[CLIENT] Đính kèm Header [x-api-key: "sk-ant-*******"] (Lớp 1: Xác thực API Key)`);
    } else if (nextIdx === 2) {
      addLog(`[CLOUD] Anthropic API chấp nhận Key và phân tích câu hỏi.`);
      addLog(`[CLOUD] AI nhận diện cần dùng công cụ "${selectedPreset.toolName}".`);
      addLog(`[CLOUD] Sinh mã định danh: "${toolUseId}" (Lớp 2: Ghép nối Context)`);
      addLog(`[CLOUD] Gửi chỉ thị gọi tool về Client.`);
    } else if (nextIdx === 3) {
      addLog(`[CLIENT] Nhận chỉ thị từ Cloud. Tên tool: "${selectedPreset.toolName}"`);
      addLog(`[CLIENT] Kiểm tra mức độ rủi ro của tool...`);
      if (selectedPreset.risk === 'high') {
        addLog(`[CLIENT] WARNING: Tool yêu cầu quyền thực thi ghi/chạy lệnh. Kích hoạt Chốt chặn duyệt tay (Lớp 4: Consent Gate)`);
      } else {
        addLog(`[CLIENT] INFO: Tool an toàn. Thực thi tự động bằng quyền hệ điều hành (Lớp 3: OS Permission)`);
      }
    } else if (nextIdx === 4) {
      if (selectedPreset.risk === 'high' && approved === null) {
        addLog(`[SYSTEM] Đang chờ người dùng phê duyệt lệnh...`);
      } else {
        executeToolAction();
      }
    } else if (nextIdx === 5) {
      addLog(`[CLIENT] Đóng gói kết quả thành công.`);
      addLog(`[CLIENT] Gửi HTTPS POST trở lại Cloud kèm [tool_use_id: "${toolUseId}"]`);
    } else if (nextIdx === 6) {
      addLog(`[CLOUD] AI nhận kết quả từ phong bì "${toolUseId}" (Đã so khớp ID).`);
      addLog(`[CLOUD] Đọc dữ liệu thực thi và hoàn thành câu trả lời.`);
    }
  };

  const handleApprove = (isApproved: boolean) => {
    setApproved(isApproved);
    if (isApproved) {
      addLog(`[USER] Đã phê duyệt! Cho phép chạy lệnh.`);
      executeToolAction();
    } else {
      addLog(`[USER] Đã từ chối! Lệnh bị hủy bỏ.`);
      setStepIndex(4);
    }
  };

  const executeToolAction = async () => {
    addLog(`[LOCAL] Tiến trình thực thi khởi chạy dưới quyền của bạn.`);
    if (mode === 'real') {
      addLog(`[LOCAL] [REAL MODE] Đang gọi API cục bộ để thực thi trực tiếp trên máy...`);
      try {
        const res = await fetch('/api/simulator/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: selectedPreset.toolName, args: selectedPreset.args })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.status === 'success') {
          addLog(`[LOCAL] [REAL MODE] Thực thi THÀNH CÔNG! Kết quả thực tế từ hệ thống:\n${data.output}`);
        } else {
          addLog(`[LOCAL] [REAL MODE] Thực thi THẤT BẠI: ${data.message || data.output}`);
        }
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        addLog(`[LOCAL] [REAL MODE] Lỗi kết nối hệ thống: ${errMsg}`);
      }
    } else {
      addLog(`[LOCAL] [SIMULATION MODE] Kết quả giả lập:\n${selectedPreset.output}`);
    }
    setStepIndex(4);
  };

  const steps: SimulationStep[] = [
    { title: 'User Prompt', desc: 'Người dùng nhập câu lệnh yêu cầu', icon: HelpCircle, status: stepIndex >= 0 ? 'completed' : 'pending', role: 'user' },
    { title: 'API Key Send', desc: 'Gửi API Key lên Cloud (Lớp 1)', icon: Key, status: stepIndex > 1 ? 'completed' : stepIndex === 1 ? 'active' : 'pending', role: 'client' },
    { title: 'AI Decides Tool', desc: 'AI phân tích & tạo mã tool_use_id (Lớp 2)', icon: Cpu, status: stepIndex > 2 ? 'completed' : stepIndex === 2 ? 'active' : 'pending', role: 'cloud' },
    { title: 'Security Route', desc: 'CLI định tuyến & kiểm tra độ rủi ro', icon: Shield, status: stepIndex > 3 ? 'completed' : stepIndex === 3 ? 'active' : 'pending', role: 'client' },
    { title: 'Local Execute', desc: 'Thực thi dưới quyền OS (Lớp 3 & 4)', icon: Terminal, status: stepIndex > 4 ? 'completed' : stepIndex === 4 ? 'active' : 'pending', role: 'local' },
    { title: 'Send Result', desc: 'Gửi kết quả kèm tool_use_id lên Cloud', icon: RefreshCw, status: stepIndex > 5 ? 'completed' : stepIndex === 5 ? 'active' : 'pending', role: 'client' },
    { title: 'Final Answer', desc: 'AI tổng hợp và in câu trả lời ra', icon: Check, status: stepIndex === 6 ? 'completed' : 'pending', role: 'cloud' }
  ];

  return (
    <div className="flex flex-col gap-6 w-full max-w-[1000px] mx-auto text-text-primary">
      {/* Intro info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-up">
        <div>
          <Title order={2} className="font-display text-text-primary mb-1">Tool Calling & Security Simulator</Title>
          <Text size="sm" c="dimmed">Mô phỏng trực quan từng bước luồng gửi yêu cầu, xác thực token và chạy lệnh cục bộ.</Text>
        </div>
        
        {/* Real/Simulation Mode Toggle */}
        <SegmentedControl
          value={mode}
          onChange={val => { setMode(val as 'simulation' | 'real'); resetSimulation(); }}
          data={[
            {
              value: 'simulation',
              label: (
                <Center style={{ gap: 6 }}>
                  <Cpu size={14} />
                  <span>Mô Phỏng (Sim)</span>
                </Center>
              ),
            },
            {
              value: 'real',
              label: (
                <Center style={{ gap: 6 }}>
                  <Zap size={14} />
                  <span>Thực Tế (Real)</span>
                </Center>
              ),
            },
          ]}
        />
      </div>

      {/* Preset Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-up stagger-1">
        {PRESETS.map(preset => (
          <Card
            key={preset.id}
            withBorder
            radius="md"
            onClick={() => { setSelectedPreset(preset); resetSimulation(); }}
            className={`glass cursor-pointer transition-all duration-300 hover-lift relative overflow-hidden ${
              selectedPreset.id === preset.id
                ? 'border-accent/40 bg-accent/[0.04]'
                : 'border-white/[0.08] hover:border-white/[0.15]'
            }`}
          >
            <Group justify="space-between" mb="xs">
              <Badge color={preset.risk === 'high' ? 'red' : 'green'} variant="light" size="sm">
                {preset.risk === 'high' ? 'High Risk' : 'Low Risk'}
              </Badge>
              {selectedPreset.id === preset.id && <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />}
            </Group>
            <Text size="sm" fw={600} className="text-text-primary">{preset.name}</Text>
            <Text size="xs" c="dimmed" mt={4} style={{ fontFamily: 'var(--font-mono)', fontStyle: 'italic' }}>"{preset.prompt}"</Text>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[350px_1fr] gap-6 items-start animate-fade-up stagger-2">
        {/* Step List Timeline */}
        <Card withBorder radius="md" p="xl" className="glass flex flex-col gap-4">
          <Text size="xs" fw={700} c="dimmed" style={{ letterSpacing: '0.15px', textTransform: 'uppercase' }} pb="xs" mb="md" className="border-b border-white/[0.08]">
            Các bước xử lý
          </Text>
          <div className="flex flex-col gap-3 relative before:absolute before:left-4.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/[0.08]">
            {steps.map((step, idx) => {
              const Icon = step.icon;
              const isActive = step.status === 'active';
              const isCompleted = step.status === 'completed';
              return (
                <div key={idx} className="flex gap-4 items-start relative z-10">
                  <div className={`h-9 w-9 rounded-lg border flex items-center justify-center shrink-0 transition-all duration-300 ${
                    isActive
                      ? 'bg-accent/10 border-accent text-accent glow-pulse'
                      : isCompleted
                      ? 'bg-success/10 border-success text-success'
                      : 'bg-white/[0.03] border-white/[0.10] text-text-muted'
                  }`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex flex-col mt-0.5">
                    <span className={`text-[12px] font-semibold ${isActive ? 'text-accent' : isCompleted ? 'text-success' : 'text-text-secondary'}`}>
                      {step.title}
                    </span>
                    <span className="text-[10px] text-text-muted mt-0.5 leading-relaxed">{step.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 pt-4 border-t border-white/[0.08] flex gap-2">
            {stepIndex < 6 && (approved !== false) ? (
              <Button
                color="indigo"
                fullWidth
                onClick={nextStep}
                leftSection={<Play size={12} />}
              >
                {stepIndex === -1 ? 'Bắt đầu' : 'Bước tiếp theo'}
              </Button>
            ) : (
              <Button
                variant="default"
                fullWidth
                onClick={resetSimulation}
              >
                Reset
              </Button>
            )}
          </div>
        </Card>

        {/* Live Simulator View */}
        <div className="flex flex-col gap-6">
          {/* Terminal / Live values */}
          <Card withBorder radius="md" p={0} className="glass overflow-hidden flex flex-col flex-1 min-h-[300px]">
            <Group justify="space-between" px="md" py="xs" className="border-b border-white/[0.08] bg-white/[0.03]">
              <Text size="xs" fw={700} c="dimmed" style={{ letterSpacing: '0.15px', textTransform: 'uppercase' }} className="flex items-center gap-2">
                <Terminal className="h-3.5 w-3.5 text-accent" /> Trạng thái hoạt động ({mode === 'real' ? 'REAL MODE' : 'SIMULATION MODE'})
              </Text>
              {stepIndex >= 0 && (
                <span className="text-[10px] bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded font-mono">
                  Mã phiên: {toolUseId.substring(0, 12)}...
                </span>
              )}
            </Group>
            <ScrollArea h={350} className="bg-bg p-5 font-mono text-[12px] leading-relaxed text-text-secondary">
              {logs.length > 0 ? (
                logs.map((log, index) => (
                  <div key={index} className="mb-1.5 animate-fade-in whitespace-pre-wrap">
                    <span className="text-accent mr-1.5">&gt;</span>
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-text-muted/70 text-center py-12">
                  <Terminal className="h-6 w-6 mx-auto mb-2 opacity-30 animate-pulse" />
                  <Text size="xs">Chọn kịch bản và nhấn "Bắt đầu" để xem luồng.</Text>
                </div>
              )}
              <div ref={terminalEndRef} />

              {/* User Consent Pop-up Simulation */}
              {stepIndex === 4 && selectedPreset.risk === 'high' && approved === null && (
                <Alert
                  color="yellow"
                  title="Yêu cầu chấp thuận (Consent Gate)"
                  icon={<Shield size={16} />}
                  mt="md"
                  className="animate-fade-up"
                >
                  <Text size="xs" mb="md" className="leading-relaxed">
                    AI đang yêu cầu chạy lệnh nguy hiểm sau: <code className="bg-black/40 px-1.5 py-0.5 rounded border border-white/10 text-success">{selectedPreset.args.CommandLine}</code>. Bạn có duyệt không?
                  </Text>
                  <Group gap="xs">
                    <Button
                      color="green"
                      size="xs"
                      onClick={() => handleApprove(true)}
                      leftSection={<Check size={14} />}
                    >
                      Đồng ý (Approve)
                    </Button>
                    <Button
                      color="red"
                      size="xs"
                      onClick={() => handleApprove(false)}
                      leftSection={<X size={14} />}
                    >
                      Từ chối (Reject)
                    </Button>
                  </Group>
                </Alert>
              )}
            </ScrollArea>
          </Card>

          {/* Security details box */}
          <Card withBorder radius="md" p="xl" className="glass">
            <Title order={5} className="text-xs font-semibold text-accent flex items-center gap-2 mb-3">
              <Info className="h-3.5 w-3.5" /> Phân tích bảo mật & Rủi ro vật lý
            </Title>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-text-secondary leading-relaxed">
              <div>
                <Text size="xs" fw={700} className="text-text-primary mb-1">🛡️ Khác biệt logic vs vật lý:</Text>
                <ul className="list-disc pl-4 space-y-1.5 text-text-muted">
                  <li><strong className="text-accent">x-api-key:</strong> Xác thực ngoài Cloud để Anthropic định danh bạn.</li>
                  <li><strong className="text-accent">tool_use_id:</strong> Dùng để ghép chính xác đầu ra vào đúng phong bì thư, không có tính năng chống hack.</li>
                  <li><strong className="text-accent">Local OS:</strong> CLI thừa hưởng quyền User máy của bạn. Đây là lý do CLI rất mạnh nhưng cũng nguy hại.</li>
                </ul>
              </div>
              <div>
                <Text size="xs" fw={700} className="text-text-primary mb-1">🚨 Nguy cơ từ thư mục `~/.claude/`:</Text>
                <Text size="xs" className="text-text-muted mb-2">
                  Thư mục này lưu trữ file chứa API key thô và toàn bộ lịch sử chat dưới dạng text thường. Nếu máy bị malware hoặc bị người khác tiếp cận, kẻ tấn công chỉ cần copy thư mục này là có thể đánh cắp sạch tài sản.
                </Text>
                <div className="bg-black/30 p-2 rounded border border-white/[0.05] font-mono text-[10px] text-accent">
                  # Khuyên dùng: Phân quyền bảo vệ thư mục<br/>
                  chmod 700 ~/.claude<br/>
                  chmod 600 ~/.claude.json
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
