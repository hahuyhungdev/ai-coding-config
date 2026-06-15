import React, { useState, useEffect, useRef } from 'react';
import { Play, Shield, Key, HelpCircle, Check, X, Terminal, Cpu, Info, RefreshCw, Zap } from 'lucide-react';

interface SimulationStep {
  title: string;
  desc: string;
  icon: any;
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
      } catch (err: any) {
        addLog(`[LOCAL] [REAL MODE] Lỗi kết nối hệ thống: ${err.message}`);
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
          <h2 className="font-display text-2xl text-text-primary mb-1">Tool Calling & Security Simulator</h2>
          <p className="text-sm text-text-muted">Mô phỏng trực quan từng bước luồng gửi yêu cầu, xác thực token và chạy lệnh cục bộ.</p>
        </div>
        
        {/* Real/Simulation Mode Toggle */}
        <div className="flex p-0.5 bg-white/[0.04] border border-white/[0.08] rounded-lg shrink-0 self-start md:self-center">
          <button
            onClick={() => { setMode('simulation'); resetSimulation(); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md cursor-pointer transition-all ${
              mode === 'simulation'
                ? 'bg-white/[0.06] text-accent'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <Cpu className="h-3.5 w-3.5" /> Mô Phỏng (Sim)
          </button>
          <button
            onClick={() => { setMode('real'); resetSimulation(); }}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md cursor-pointer transition-all ${
              mode === 'real'
                ? 'bg-accent/10 border border-accent/20 text-accent glow-pulse'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <Zap className="h-3.5 w-3.5" /> Thực Tế (Real)
          </button>
        </div>
      </div>

      {/* Preset Selector */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-up stagger-1">
        {PRESETS.map(preset => (
          <div
            key={preset.id}
            onClick={() => { setSelectedPreset(preset); resetSimulation(); }}
            className={`glass rounded-xl p-5 cursor-pointer transition-all duration-300 hover-lift relative overflow-hidden ${
              selectedPreset.id === preset.id
                ? 'border-accent/40 bg-accent/[0.04]'
                : 'border-white/[0.08] hover:border-white/[0.15]'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase ${
                preset.risk === 'high' ? 'bg-error/10 text-error border border-error/15' : 'bg-success/10 text-success border border-success/15'
              }`}>
                {preset.risk === 'high' ? 'High Risk' : 'Low Risk'}
              </span>
              {selectedPreset.id === preset.id && <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />}
            </div>
            <h3 className="text-[14px] font-semibold text-text-primary">{preset.name}</h3>
            <p className="text-xs text-text-muted mt-1 font-mono italic">"{preset.prompt}"</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[350px_1fr] gap-6 items-start animate-fade-up stagger-2">
        {/* Step List Timeline */}
        <div className="glass rounded-xl p-5 flex flex-col gap-4">
          <h4 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider pb-3 border-b border-white/[0.08]">
            Các bước xử lý
          </h4>
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
              <button
                onClick={nextStep}
                className="flex-1 py-2 bg-accent text-bg text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 cursor-pointer hover:bg-accent-hover transition-colors"
              >
                <Play className="h-3 w-3" /> {stepIndex === -1 ? 'Bắt đầu' : 'Bước tiếp theo'}
              </button>
            ) : (
              <button
                onClick={resetSimulation}
                className="flex-1 py-2 bg-white/[0.05] hover:bg-white/[0.08] text-text-secondary border border-white/[0.10] text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
              >
                Reset
              </button>
            )}
          </div>
        </div>

        {/* Live Simulator View */}
        <div className="flex flex-col gap-6">
          {/* Terminal / Live values */}
          <div className="glass rounded-xl overflow-hidden flex flex-col flex-1 min-h-[300px]">
            <div className="border-b border-white/[0.08] px-5 py-3 flex items-center justify-between bg-white/[0.03]">
              <div className="text-[11px] font-semibold text-text-muted uppercase tracking-[0.12] flex items-center gap-2">
                <Terminal className="h-3.5 w-3.5 text-accent" /> Trạng thái hoạt động ({mode === 'real' ? 'REAL MODE' : 'SIMULATION MODE'})
              </div>
              {stepIndex >= 0 && (
                <span className="text-[10px] bg-accent/10 text-accent border border-accent/20 px-2 py-0.5 rounded font-mono">
                  Mã phiên: {toolUseId.substring(0, 12)}...
                </span>
              )}
            </div>
            <div className="flex-1 bg-bg p-5 font-mono text-[12px] leading-relaxed text-text-secondary overflow-y-auto max-h-[350px]">
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
                  <p>Chọn kịch bản và nhấn "Bắt đầu" để xem luồng.</p>
                </div>
              )}
              <div ref={terminalEndRef} />

              {/* User Consent Pop-up Simulation */}
              {stepIndex === 4 && selectedPreset.risk === 'high' && approved === null && (
                <div className="mt-4 p-4 border border-warning/30 bg-warning/[0.04] rounded-lg animate-fade-up">
                  <div className="flex items-center gap-2 text-warning mb-2">
                    <Shield className="h-4 w-4" />
                    <span className="font-semibold text-xs uppercase tracking-wide">Yêu cầu chấp thuận (Consent Gate)</span>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed mb-4">
                    AI đang yêu cầu chạy lệnh nguy hiểm sau: <code className="bg-black/40 px-1.5 py-0.5 rounded border border-white/10 text-success">{selectedPreset.args.CommandLine}</code>. Bạn có duyệt không?
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApprove(true)}
                      className="px-3.5 py-1.5 bg-success text-bg font-semibold text-xs rounded-md flex items-center gap-1.5 cursor-pointer hover:bg-success/90 transition-colors"
                    >
                      <Check className="h-3.5 w-3.5" /> Đồng ý (Approve)
                    </button>
                    <button
                      onClick={() => handleApprove(false)}
                      className="px-3.5 py-1.5 bg-error text-text-primary font-semibold text-xs rounded-md flex items-center gap-1.5 cursor-pointer hover:bg-error/90 transition-colors"
                    >
                      <X className="h-3.5 w-3.5" /> Từ chối (Reject)
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Security details box */}
          <div className="glass rounded-xl p-5 border border-white/[0.08]">
            <h5 className="text-xs font-semibold text-accent flex items-center gap-2 mb-3">
              <Info className="h-3.5 w-3.5" /> Phân tích bảo mật & Rủi ro vật lý
            </h5>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-text-secondary leading-relaxed">
              <div>
                <p className="font-semibold text-text-primary mb-1">🛡️ Khác biệt logic vs vật lý:</p>
                <ul className="list-disc pl-4 space-y-1.5 text-text-muted">
                  <li><strong className="text-accent">x-api-key:</strong> Xác thực ngoài Cloud để Anthropic định danh bạn.</li>
                  <li><strong className="text-accent">tool_use_id:</strong> Dùng để ghép chính xác đầu ra vào đúng phong bì thư, không có tính năng chống hack.</li>
                  <li><strong className="text-accent">Local OS:</strong> CLI thừa hưởng quyền User máy của bạn. Đây là lý do CLI rất mạnh nhưng cũng nguy hại.</li>
                </ul>
              </div>
              <div>
                <p className="font-semibold text-text-primary mb-1">🚨 Nguy cơ từ thư mục `~/.claude/`:</p>
                <p className="text-text-muted mb-2">
                  Thư mục này lưu trữ file chứa API key thô và toàn bộ lịch sử chat dưới dạng text thường. Nếu máy bị malware hoặc bị người khác tiếp cận, kẻ tấn công chỉ cần copy thư mục này là có thể đánh cắp sạch tài sản.
                </p>
                <div className="bg-black/30 p-2 rounded border border-white/[0.05] font-mono text-[10px] text-accent">
                  # Khuyên dùng: Phân quyền bảo vệ thư mục<br/>
                  chmod 700 ~/.claude<br/>
                  chmod 600 ~/.claude.json
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
