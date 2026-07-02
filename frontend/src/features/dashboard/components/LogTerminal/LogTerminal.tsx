import React, { useRef, useEffect } from 'react';
import { Terminal as TerminalIcon, Trash } from 'lucide-react';
import { Button, Text, Group } from '@mantine/core';

interface LogTerminalProps {
  logs: string[];
  setLogs: React.Dispatch<React.SetStateAction<string[]>>;
}

export const LogTerminal: React.FC<LogTerminalProps> = ({ logs, setLogs }) => {
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const ansiToHtml = (text: string) => {
    const ansiMap: Record<string, string> = {
      '31': 'text-red-400 font-bold',
      '32': 'text-emerald-400 font-bold',
      '33': 'text-amber-400 font-bold',
      '34': 'text-sky-400 font-bold',
      '35': 'text-fuchsia-400 font-bold',
      '36': 'text-cyan-400 font-bold',
      '90': 'text-slate-500',
      '91': 'text-red-400',
      '92': 'text-emerald-400',
      '93': 'text-amber-400',
      '94': 'text-sky-400',
    };

    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const regex = new RegExp(String.fromCharCode(27) + '\\[(\\d+(?:;\\d+)*)m', 'g');
    let openSpans = 0;

    html = html.replace(regex, (_, codes) => {
      let replacement = '';
      const codeArray = codes.split(';');
      for (const code of codeArray) {
        if (code === '0') {
          while (openSpans > 0) {
            replacement += '</span>';
            openSpans--;
          }
        } else if (ansiMap[code]) {
          replacement += `<span class="${ansiMap[code]}">`;
          openSpans++;
        }
      }
      return replacement;
    });

    while (openSpans > 0) {
      html += '</span>';
      openSpans--;
    }

    return <div dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <div className="glass rounded-xl overflow-hidden flex flex-col flex-1 min-h-[360px] border border-white/[0.08] animate-fade-up stagger-4 shadow-xl">
      {/* Terminal Header */}
      <div className="border-b border-white/[0.06] px-5 py-3 flex items-center justify-between bg-black/20 backdrop-blur-sm">
        <div className="flex items-center gap-6">
          {/* macOS window dots */}
          <div className="flex gap-1.5 shrink-0">
            <span className="h-3 w-3 rounded-full bg-red-500/80 border border-red-600/30" />
            <span className="h-3 w-3 rounded-full bg-amber-500/80 border border-amber-600/30" />
            <span className="h-3 w-3 rounded-full bg-emerald-500/80 border border-emerald-600/30" />
          </div>
          <Group gap="xs">
            <TerminalIcon size={14} className="text-accent/60" />
            <Text size="10px" fw={700} c="dimmed" style={{ textTransform: 'uppercase', letterSpacing: '1px' }}>
              Process Output
            </Text>
          </Group>
        </div>
        <Button
          variant="subtle"
          color="red"
          size="xs"
          leftSection={<Trash size={12} />}
          onClick={() => setLogs([])}
        >
          Clear
        </Button>
      </div>

      {/* Terminal body - sleek dark style */}
      <div
        ref={logContainerRef}
        className="flex-1 bg-slate-950 p-5 font-mono text-[12px] leading-relaxed text-slate-300 overflow-y-auto max-h-[420px] shadow-inner select-text custom-terminal-scrollbar"
      >
        {logs.length > 0 ? (
          <div className="flex flex-col gap-1">
            {logs.map((log, index) => (
              <div key={index} className="break-all font-mono">
                {ansiToHtml(log)}
              </div>
            ))}
            {/* Pulsing command cursor */}
            <div className="flex items-center gap-1 mt-1">
              <span className="text-accent font-bold">$</span>
              <span className="h-3 w-1.5 bg-accent/80 animate-pulse" />
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 py-12">
            <TerminalIcon className="h-8 w-8 mb-3 opacity-20 text-slate-400 animate-pulse" />
            <p className="text-xs font-semibold">Terminal idle. Logs will display here during operations.</p>
            <p className="text-[10px] opacity-75 mt-1 font-mono">$ tail -f /dev/null</p>
          </div>
        )}
      </div>
    </div>
  );
};
